"""Deterministic employee seed (`Random(42)`, no Faker)."""

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from random import Random
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.db import SCHEMA_STATEMENTS, create_db_engine, init_schema
from app.models import Employee
from app.money import decimal_to_scaled, scaled_to_decimal
from app.settings import Settings

_FX_SCALE = 6
_INSERT_BATCH_SIZE = 1000
_CURRENCY_UPDATED_AT = "2026-01-01T00:00:00Z"
_TERMINATED_RATE = 0.04
_HIRE_ORIGIN = date(2016, 1, 1)
_HIRE_DAYS = (date(2025, 12, 31) - _HIRE_ORIGIN).days + 1
# Major-unit payroll grid before scaling. JPY has no minor units.
_MAJOR_INCREMENT = {0: Decimal(10000), 2: Decimal(500)}


class CurrencySpec(NamedTuple):
    code: str
    name: str
    minor_scale: int
    units_per_usd_scaled: str


class CountrySpec(NamedTuple):
    code: str
    name: str
    currency_code: str
    weight: int


class DepartmentSpec(NamedTuple):
    id: int
    name: str
    weight: int


class LevelSpec(NamedTuple):
    name: str
    weight: int
    usd_low: int
    usd_high: int


# Sample planning rates. `units_per_usd_scaled` is scale 6, not minor_scale.
CURRENCIES: tuple[CurrencySpec, ...] = (
    CurrencySpec("USD", "US Dollar", 2, "1000000"),
    CurrencySpec("GBP", "British Pound", 2, "780000"),
    CurrencySpec("EUR", "Euro", 2, "920000"),
    CurrencySpec("INR", "Indian Rupee", 2, "83500000"),
    CurrencySpec("SGD", "Singapore Dollar", 2, "1340000"),
    CurrencySpec("JPY", "Japanese Yen", 0, "149000000"),
    CurrencySpec("CAD", "Canadian Dollar", 2, "1360000"),
    CurrencySpec("AUD", "Australian Dollar", 2, "1520000"),
)

# India and the United States are the two heaviest weights.
COUNTRIES: tuple[CountrySpec, ...] = (
    CountrySpec("US", "United States", "USD", 24),
    CountrySpec("GB", "United Kingdom", "GBP", 10),
    CountrySpec("DE", "Germany", "EUR", 8),
    CountrySpec("IN", "India", "INR", 30),
    CountrySpec("SG", "Singapore", "SGD", 6),
    CountrySpec("JP", "Japan", "JPY", 6),
    CountrySpec("CA", "Canada", "CAD", 8),
    CountrySpec("AU", "Australia", "AUD", 8),
)

# Engineering is the largest department.
DEPARTMENTS: tuple[DepartmentSpec, ...] = (
    DepartmentSpec(1, "Engineering", 40),
    DepartmentSpec(2, "Product", 12),
    DepartmentSpec(3, "Sales", 14),
    DepartmentSpec(4, "People", 8),
    DepartmentSpec(5, "Finance", 12),
    DepartmentSpec(6, "Operations", 14),
)

# Many IC2 and IC3, few M2. Bands are USD equivalent before FX.
LEVELS: tuple[LevelSpec, ...] = (
    LevelSpec("IC1", 10, 40_000, 65_000),
    LevelSpec("IC2", 28, 62_000, 98_000),
    LevelSpec("IC3", 26, 92_000, 135_000),
    LevelSpec("IC4", 14, 125_000, 175_000),
    LevelSpec("IC5", 10, 160_000, 215_000),
    LevelSpec("M1", 8, 190_000, 245_000),
    LevelSpec("M2", 4, 225_000, 280_000),
)

FIRST_NAMES: tuple[str, ...] = (
    "Aarav",
    "Aditi",
    "Amelia",
    "Ananya",
    "Arjun",
    "Benjamin",
    "Chloe",
    "Daniel",
    "Diya",
    "Emma",
    "Ethan",
    "Fatima",
    "Gabriel",
    "Hannah",
    "Hiro",
    "Ishaan",
    "Jack",
    "Kabir",
    "Liam",
    "Lucas",
    "Maya",
    "Mei",
    "Noah",
    "Nora",
    "Olivia",
    "Priya",
    "Rahul",
    "Sofia",
    "Vihaan",
    "William",
    "Zara",
    "Elena",
)

LAST_NAMES: tuple[str, ...] = (
    "Anderson",
    "Brown",
    "Chen",
    "Davis",
    "Garcia",
    "Gupta",
    "Iyer",
    "Johnson",
    "Kapoor",
    "Kim",
    "Kumar",
    "Lee",
    "Martinez",
    "Miller",
    "Nair",
    "Nguyen",
    "Patel",
    "Reddy",
    "Rossi",
    "Sato",
    "Schmidt",
    "Sharma",
    "Singh",
    "Smith",
    "Tanaka",
    "Taylor",
    "Thomas",
    "Walker",
    "Wilson",
    "Wright",
)

# Index matches LEVELS. Titles stay fixed so they do not draw extra randomness.
_TITLE_LADDERS: dict[str, tuple[str, ...]] = {
    "Engineering": (
        "Associate Software Engineer",
        "Software Engineer",
        "Senior Software Engineer",
        "Staff Software Engineer",
        "Principal Software Engineer",
        "Engineering Manager",
        "Director of Engineering",
    ),
    "Product": (
        "Associate Product Manager",
        "Product Manager",
        "Senior Product Manager",
        "Staff Product Manager",
        "Principal Product Manager",
        "Group Product Manager",
        "Director of Product",
    ),
    "Sales": (
        "Sales Development Representative",
        "Account Executive",
        "Senior Account Executive",
        "Strategic Account Executive",
        "Principal Account Executive",
        "Sales Manager",
        "Director of Sales",
    ),
    "People": (
        "People Coordinator",
        "People Partner",
        "Senior People Partner",
        "Lead People Partner",
        "Principal People Partner",
        "People Manager",
        "Director of People",
    ),
    "Finance": (
        "Finance Analyst",
        "Accountant",
        "Senior Accountant",
        "Lead Accountant",
        "Principal Accountant",
        "Finance Manager",
        "Director of Finance",
    ),
    "Operations": (
        "Operations Coordinator",
        "Operations Associate",
        "Senior Operations Associate",
        "Operations Lead",
        "Principal Operations Lead",
        "Operations Manager",
        "Director of Operations",
    ),
}

_LEVEL_INDEX = {level.name: index for index, level in enumerate(LEVELS)}
_COUNTRY_WEIGHTS = tuple(country.weight for country in COUNTRIES)
_DEPARTMENT_WEIGHTS = tuple(department.weight for department in DEPARTMENTS)
_LEVEL_WEIGHTS = tuple(level.weight for level in LEVELS)
_CURRENCIES_BY_CODE = {currency.code: currency for currency in CURRENCIES}


@dataclass(frozen=True, slots=True)
class SeedEmployee:
    id: str
    employee_number: str
    first_name: str
    last_name: str
    email: str
    job_title: str
    department_id: int
    country_code: str
    currency_code: str
    level: str
    base_salary_scaled: str
    variable_pay_scaled: str
    salary_usd_scaled: str
    status: str
    hire_date: str
    comp_effective_date: str
    version_id: int
    created_at: str
    updated_at: str


def generate_employees(count: int) -> list[SeedEmployee]:
    """Return `count` employees from `Random(42)`.

    The same count always returns the same rows. A shorter count is a prefix
    of a longer one because the generator is restarted from seed 42.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    rng = Random(42)
    return [_one_employee(rng, number) for number in range(1, count + 1)]


def _one_employee(rng: Random, number: int) -> SeedEmployee:
    # Call order is part of the golden row. Do not reorder these draws.
    employee_id = str(UUID(int=rng.getrandbits(128)))
    first_name = rng.choice(FIRST_NAMES)
    last_name = rng.choice(LAST_NAMES)
    country = _pick_weighted(rng, COUNTRIES, _COUNTRY_WEIGHTS)
    department = _pick_weighted(rng, DEPARTMENTS, _DEPARTMENT_WEIGHTS)
    level = _pick_weighted(rng, LEVELS, _LEVEL_WEIGHTS)
    usd_base = rng.randint(level.usd_low, level.usd_high)
    if department.name == "Sales":
        variable_percent = rng.randint(10, 20)
    else:
        variable_percent = 0
    status = "terminated" if rng.random() < _TERMINATED_RATE else "active"
    hired = _HIRE_ORIGIN + timedelta(days=rng.randrange(_HIRE_DAYS))
    hired_on = hired.isoformat()
    stamp = f"{hired_on}T00:00:00Z"
    currency = _CURRENCIES_BY_CODE[country.currency_code]
    base_scaled, variable_scaled, usd_scaled = _scaled_pay(
        usd_base,
        variable_percent,
        currency.minor_scale,
        currency.units_per_usd_scaled,
    )
    return SeedEmployee(
        id=employee_id,
        employee_number=f"EMP-{number:05d}",
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name}.{last_name}.{number}@acme.test".lower(),
        job_title=_TITLE_LADDERS[department.name][_LEVEL_INDEX[level.name]],
        department_id=department.id,
        country_code=country.code,
        currency_code=currency.code,
        level=level.name,
        base_salary_scaled=base_scaled,
        variable_pay_scaled=variable_scaled,
        salary_usd_scaled=usd_scaled,
        status=status,
        hire_date=hired_on,
        comp_effective_date=hired_on,
        version_id=1,
        created_at=stamp,
        updated_at=stamp,
    )


def _pick_weighted[T](rng: Random, items: Sequence[T], weights: Sequence[int]) -> T:
    point = rng.randrange(sum(weights))
    running = 0
    for item, weight in zip(items, weights, strict=True):
        running += weight
        if point < running:
            return item
    raise RuntimeError("weighted pick missed every bucket")


def _payroll_round(amount: Decimal, minor_scale: int) -> Decimal:
    increment = _MAJOR_INCREMENT[minor_scale]
    steps = (amount / increment).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return steps * increment


def _scaled_pay(
    usd_base: int,
    variable_percent: int,
    minor_scale: int,
    units_per_usd_scaled: str,
) -> tuple[str, str, str]:
    units_per_usd = scaled_to_decimal(units_per_usd_scaled, _FX_SCALE)
    local_base = _payroll_round(Decimal(usd_base) * units_per_usd, minor_scale)
    if variable_percent:
        local_variable = _payroll_round(
            local_base * Decimal(variable_percent) / Decimal(100),
            minor_scale,
        )
        if local_variable <= 0:
            local_variable = _MAJOR_INCREMENT[minor_scale]
    else:
        local_variable = Decimal(0)
    base_scaled = decimal_to_scaled(local_base, minor_scale)
    variable_scaled = decimal_to_scaled(local_variable, minor_scale)
    # Re-derive USD from the stored digit strings, not from the pre-scale amounts.
    local = scaled_to_decimal(base_scaled, minor_scale) + scaled_to_decimal(
        variable_scaled, minor_scale
    )
    usd = local / scaled_to_decimal(units_per_usd_scaled, _FX_SCALE)
    return base_scaled, variable_scaled, decimal_to_scaled(usd, 2)


async def apply_seed(engine: AsyncEngine, count: int, *, reset: bool) -> int:
    """Upsert reference rows and insert `count` employees.

    Without ``reset``, a non-empty employee table is left in place.
    ``reset`` deletes audit rows and employees, then inserts again.
    Returns the number of employee rows inserted.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if count > 0 and not reset:
        async with engine.connect() as conn:
            counted = await conn.exec_driver_sql("SELECT COUNT(*) FROM employees")
            existing = int(counted.scalar_one())
        if existing:
            async with engine.begin() as conn:
                await _upsert_reference(conn, restore_rates=False)
            return 0

    rows = generate_employees(count) if count else []
    async with engine.begin() as conn:
        await _upsert_reference(conn, restore_rates=reset)
        if reset:
            await _clear_people(conn)

    for start in range(0, len(rows), _INSERT_BATCH_SIZE):
        batch = [asdict(row) for row in rows[start : start + _INSERT_BATCH_SIZE]]
        async with engine.begin() as conn:
            await conn.execute(insert(Employee), batch)

    if reset or rows:
        async with engine.begin() as conn:
            # Triggers may already have written the index. Rebuild once.
            await conn.exec_driver_sql(
                "INSERT INTO employees_fts(employees_fts) VALUES('rebuild')"
            )
    return len(rows)


async def seed_if_empty(engine: AsyncEngine, count: int) -> None:
    """Seed `count` employees when the table is empty and `count` is positive."""
    if count <= 0:
        return
    async with engine.connect() as conn:
        existing = int((await conn.exec_driver_sql("SELECT COUNT(*) FROM employees")).scalar_one())
    if existing == 0:
        await apply_seed(engine, count, reset=False)


async def _upsert_reference(conn: AsyncConnection, *, restore_rates: bool) -> None:
    rate_update = (
        """,
              units_per_usd_scaled = excluded.units_per_usd_scaled,
              updated_at = excluded.updated_at"""
        if restore_rates
        else ""
    )
    for currency in CURRENCIES:
        await conn.exec_driver_sql(
            f"""
            INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
              name = excluded.name,
              minor_scale = excluded.minor_scale{rate_update}
            """,
            (
                currency.code,
                currency.name,
                currency.minor_scale,
                currency.units_per_usd_scaled,
                _CURRENCY_UPDATED_AT,
            ),
        )
    for country in COUNTRIES:
        await conn.exec_driver_sql(
            """
            INSERT INTO countries (code, name, currency_code)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
              name = excluded.name,
              currency_code = excluded.currency_code
            """,
            (country.code, country.name, country.currency_code),
        )
    for department in DEPARTMENTS:
        await conn.exec_driver_sql(
            """
            INSERT INTO departments (id, name)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name
            """,
            (department.id, department.name),
        )


def _audit_delete_trigger_sql() -> str:
    for statement in SCHEMA_STATEMENTS:
        if "compensation_audit_logs_no_delete" in statement:
            return statement
    raise RuntimeError("audit delete trigger is missing from SCHEMA_STATEMENTS")


async def _clear_people(conn: AsyncConnection) -> None:
    # Audit rows are append-only. Drop that trigger for this delete, then put it back.
    await conn.exec_driver_sql("DROP TRIGGER IF EXISTS compensation_audit_logs_no_delete")
    await conn.exec_driver_sql("DELETE FROM compensation_audit_logs")
    await conn.exec_driver_sql(_audit_delete_trigger_sql())
    await conn.exec_driver_sql("DELETE FROM employees")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed",
        description="Seed CompPulse employees",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Employees to insert (default: settings.seed_count)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete audit rows and employees, then seed",
    )
    args = parser.parse_args(argv)
    if args.count is not None and args.count < 0:
        parser.error("--count must be >= 0")
    settings = Settings()
    count = settings.seed_count if args.count is None else args.count
    inserted = asyncio.run(_run_cli(settings.database_url, count, reset=args.reset))
    print(f"seeded {inserted} employees")


async def _run_cli(database_url: str, count: int, *, reset: bool) -> int:
    engine = create_db_engine(database_url)
    try:
        await init_schema(engine)
        return await apply_seed(engine, count, reset=reset)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    main()
