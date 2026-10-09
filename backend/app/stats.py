import statistics
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.money import decimal_to_scaled, scaled_to_decimal

# Lower bound inclusive, upper exclusive. The last bucket is open.
# Negative USD amounts fall in the first bucket. The dash is U+2013.
_HISTOGRAM_BUCKETS: tuple[tuple[str, Decimal | None], ...] = (
    ("0\u201350k", Decimal(50_000)),
    ("50\u201375k", Decimal(75_000)),
    ("75\u2013100k", Decimal(100_000)),
    ("100\u2013150k", Decimal(150_000)),
    ("150\u2013200k", Decimal(200_000)),
    ("200\u2013300k", Decimal(300_000)),
    ("300k+", None),
)


class DepartmentBreakdown(BaseModel):
    department_id: int
    department_name: str
    headcount: int
    total_salary_usd_scaled: str
    average_salary_usd_scaled: str


class CountryBreakdown(BaseModel):
    country_code: str
    country_name: str
    headcount: int
    total_salary_usd_scaled: str
    average_salary_usd_scaled: str


class HistogramBucket(BaseModel):
    label: str
    count: int


class AnalyticsOverview(BaseModel):
    headcount: int
    total_salary_usd_scaled: str
    salary_usd_scale: int
    average_salary_usd_scaled: str
    p25_salary_usd_scaled: str
    p50_salary_usd_scaled: str
    p75_salary_usd_scaled: str
    by_department: list[DepartmentBreakdown]
    by_country: list[CountryBreakdown]
    histogram: list[HistogramBucket]


def _average_scaled(sum_cents: int, count: int) -> str:
    if count == 0:
        return "0"
    # SQLite AVG is a float. Mean stays Decimal through half-even cents.
    return decimal_to_scaled(Decimal(sum_cents) / Decimal(100) / Decimal(count), 2)


def _quartiles(amounts: list[Decimal]) -> tuple[str, str, str]:
    # quantiles() raises below two points. An empty active set is all zeros.
    if len(amounts) < 2:
        if not amounts:
            return ("0", "0", "0")
        only = decimal_to_scaled(amounts[0], 2)
        return (only, only, only)
    p25, p50, p75 = statistics.quantiles(amounts, n=4, method="inclusive")
    return (
        decimal_to_scaled(p25, 2),
        decimal_to_scaled(p50, 2),
        decimal_to_scaled(p75, 2),
    )


def _histogram(amounts: list[Decimal]) -> list[HistogramBucket]:
    counts = [0] * len(_HISTOGRAM_BUCKETS)
    for amount in amounts:
        for index, (_, upper) in enumerate(_HISTOGRAM_BUCKETS):
            if upper is None or amount < upper:
                counts[index] += 1
                break
    return [
        HistogramBucket(label=label, count=counts[index])
        for index, (label, _) in enumerate(_HISTOGRAM_BUCKETS)
    ]


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("aggregate must be an integer")
    return value


async def load_overview(session: AsyncSession) -> AnalyticsOverview:
    total = (
        await session.execute(
            text(
                """
                SELECT COUNT(*) AS headcount,
                       SUM(CAST(salary_usd_scaled AS INTEGER)) AS total_cents
                FROM employees
                WHERE status = 'active'
                """
            )
        )
    ).one()
    headcount = _as_int(total.headcount)
    total_cents = 0 if total.total_cents is None else _as_int(total.total_cents)

    salary_rows = (
        await session.execute(
            text(
                """
                SELECT salary_usd_scaled
                FROM employees
                WHERE status = 'active'
                """
            )
        )
    ).scalars()
    amounts = [scaled_to_decimal(value, 2) for value in salary_rows]
    p25, p50, p75 = _quartiles(amounts)

    departments = (
        await session.execute(
            text(
                """
                SELECT departments.id AS department_id,
                       departments.name AS department_name,
                       COUNT(*) AS headcount,
                       SUM(CAST(employees.salary_usd_scaled AS INTEGER)) AS total_cents
                FROM employees
                JOIN departments ON departments.id = employees.department_id
                WHERE employees.status = 'active'
                GROUP BY departments.id, departments.name
                HAVING COUNT(*) > 0
                ORDER BY departments.name
                """
            )
        )
    ).mappings()
    countries = (
        await session.execute(
            text(
                """
                SELECT countries.code AS country_code,
                       countries.name AS country_name,
                       COUNT(*) AS headcount,
                       SUM(CAST(employees.salary_usd_scaled AS INTEGER)) AS total_cents
                FROM employees
                JOIN countries ON countries.code = employees.country_code
                WHERE employees.status = 'active'
                GROUP BY countries.code, countries.name
                HAVING COUNT(*) > 0
                ORDER BY countries.name
                """
            )
        )
    ).mappings()

    return AnalyticsOverview(
        headcount=headcount,
        total_salary_usd_scaled=str(total_cents),
        salary_usd_scale=2,
        average_salary_usd_scaled=_average_scaled(total_cents, headcount),
        p25_salary_usd_scaled=p25,
        p50_salary_usd_scaled=p50,
        p75_salary_usd_scaled=p75,
        by_department=[
            DepartmentBreakdown(
                department_id=_as_int(row["department_id"]),
                department_name=str(row["department_name"]),
                headcount=_as_int(row["headcount"]),
                total_salary_usd_scaled=str(_as_int(row["total_cents"])),
                average_salary_usd_scaled=_average_scaled(
                    _as_int(row["total_cents"]), _as_int(row["headcount"])
                ),
            )
            for row in departments
        ],
        by_country=[
            CountryBreakdown(
                country_code=str(row["country_code"]),
                country_name=str(row["country_name"]),
                headcount=_as_int(row["headcount"]),
                total_salary_usd_scaled=str(_as_int(row["total_cents"])),
                average_salary_usd_scaled=_average_scaled(
                    _as_int(row["total_cents"]), _as_int(row["headcount"])
                ),
            )
            for row in countries
        ],
        histogram=_histogram(amounts),
    )
