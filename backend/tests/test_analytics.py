import asyncio
import sqlite3
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import create_db_engine, init_schema
from app.deps import issue_token
from app.main import create_app
from app.settings import Settings

_HISTOGRAM_LABELS = (
    "0\u201350k",
    "50\u201375k",
    "75\u2013100k",
    "100\u2013150k",
    "150\u2013200k",
    "200\u2013300k",
    "300k+",
)


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def _auth(settings: Settings, email: str | None = None) -> dict[str, str]:
    token = issue_token(settings.app_secret, settings.hr_email if email is None else email)
    return {"Authorization": f"Bearer {token}"}


def _prepare(tmp_path: Path, seed: Callable[[sqlite3.Connection], None]) -> Settings:
    db_path = tmp_path / "analytics.db"
    url = _sqlite_url(db_path)
    engine = create_db_engine(url)

    async def _init() -> None:
        await init_schema(engine)
        await engine.dispose()

    asyncio.run(_init())
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        _seed_reference(connection)
        seed(connection)
        connection.commit()
    finally:
        connection.close()
    return Settings(
        database_url=url,
        seed_count=0,
        app_secret="test-secret",
        hr_email="hr@acme.test",
    )


def _seed_reference(connection: sqlite3.Connection) -> None:
    connection.executemany(
        "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
        "VALUES (?, ?, 2, ?, '2026-01-01T00:00:00Z')",
        [
            ("USD", "US Dollar", "1000000"),
            ("INR", "Indian Rupee", "83000000"),
            ("GBP", "Pound Sterling", "780000"),
            ("EUR", "Euro", "920000"),
        ],
    )
    connection.executemany(
        "INSERT INTO countries (code, name, currency_code) VALUES (?, ?, ?)",
        [
            ("US", "United States", "USD"),
            ("IN", "India", "INR"),
            ("GB", "United Kingdom", "GBP"),
            ("DE", "Germany", "EUR"),
        ],
    )
    # Insert out of name order so the response sort is not insertion order.
    connection.executemany(
        "INSERT INTO departments (id, name) VALUES (?, ?)",
        [(3, "Sales"), (4, "People"), (1, "Engineering"), (2, "Finance")],
    )


def _insert_employee(
    connection: sqlite3.Connection,
    employee_id: str,
    department_id: int,
    country_code: str,
    currency_code: str,
    salary_usd_scaled: str,
    status: str = "active",
) -> None:
    connection.execute(
        """
        INSERT INTO employees (
          id, employee_number, first_name, last_name, email, job_title,
          department_id, country_code, currency_code, level,
          base_salary_scaled, variable_pay_scaled, salary_usd_scaled,
          status, hire_date, comp_effective_date, version_id, created_at, updated_at
        ) VALUES (
          ?, ?, 'Ada', 'Lovelace', ?, 'Engineer',
          ?, ?, ?, 'IC3',
          ?, '0', ?,
          ?, '2021-03-15', '2025-04-01', 1, '2021-03-15T00:00:00Z', '2025-04-01T00:00:00Z'
        )
        """,
        (
            employee_id,
            f"EMP-{employee_id}",
            f"{employee_id}@acme.test",
            department_id,
            country_code,
            currency_code,
            salary_usd_scaled,
            salary_usd_scaled,
            status,
        ),
    )


def _overview(settings: Settings, headers: dict[str, str] | None = None) -> dict[str, object]:
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/analytics/overview", headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    _assert_no_floats(body)
    return body


def _assert_no_floats(value: object) -> None:
    if isinstance(value, float):
        raise AssertionError(value)
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_floats(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_floats(item)


def _histogram(counts: tuple[int, int, int, int, int, int, int]) -> list[dict[str, object]]:
    return [
        {"label": label, "count": count}
        for label, count in zip(_HISTOGRAM_LABELS, counts, strict=True)
    ]


def test_requires_hr_bearer(tmp_path: Path) -> None:
    settings = _prepare(tmp_path, lambda _connection: None)
    app = create_app(settings)
    with TestClient(app) as client:
        missing = client.get("/analytics/overview")
        assert missing.status_code == 401
        assert missing.json() == {"detail": "Not authenticated"}

        wrong_scheme = client.get("/analytics/overview", headers={"Authorization": "Basic abc"})
        assert wrong_scheme.status_code == 401

        forged = issue_token("other-secret", settings.hr_email)
        bad_signature = client.get(
            "/analytics/overview", headers={"Authorization": f"Bearer {forged}"}
        )
        assert bad_signature.status_code == 401

        other = client.get(
            "/analytics/overview",
            headers=_auth(settings, "someone@acme.test"),
        )
        assert other.status_code == 401
        assert other.json() == {"detail": "Not authenticated"}


def test_empty_active_set_is_zero(tmp_path: Path) -> None:
    def seed(connection: sqlite3.Connection) -> None:
        _insert_employee(connection, "term", 4, "DE", "EUR", "999999999", status="terminated")

    settings = _prepare(tmp_path, seed)
    body = _overview(settings, _auth(settings))
    assert body == {
        "headcount": 0,
        "total_salary_usd_scaled": "0",
        "salary_usd_scale": 2,
        "average_salary_usd_scaled": "0",
        "p25_salary_usd_scaled": "0",
        "p50_salary_usd_scaled": "0",
        "p75_salary_usd_scaled": "0",
        "by_department": [],
        "by_country": [],
        "histogram": _histogram((0, 0, 0, 0, 0, 0, 0)),
    }


def test_quartiles_exclude_terminated_employee(tmp_path: Path) -> None:
    # Active USD salaries, sorted, even count, with a tie at 50000:
    #   40000, 50000, 50000, 80000, 120000, 300000
    # inclusive quartiles: m = 6 - 1 = 5, n = 4
    #   p25: divmod(1 * 5, 4) = (1, 1)
    #        (50000 * 3 + 50000 * 1) / 4 = 50000 → "5000000"
    #   p50: divmod(2 * 5, 4) = (2, 2)
    #        (50000 * 2 + 80000 * 2) / 4 = 65000 → "6500000"
    #   p75: divmod(3 * 5, 4) = (3, 3)
    #        (80000 * 1 + 120000 * 3) / 4 = 110000 → "11000000"
    # Sum of those cents is 64000000. The terminated row is 999999999 cents
    # and must not change headcount or that total.
    def seed(connection: sqlite3.Connection) -> None:
        rows = [
            ("a1", 1, "US", "USD", "4000000", "active"),
            ("a2", 1, "US", "USD", "5000000", "active"),
            ("a3", 1, "IN", "INR", "5000000", "active"),
            ("a4", 2, "GB", "GBP", "8000000", "active"),
            ("a5", 2, "IN", "INR", "12000000", "active"),
            ("a6", 3, "US", "USD", "30000000", "active"),
            ("t1", 1, "US", "USD", "999999999", "terminated"),
            ("t2", 4, "DE", "EUR", "888888888", "terminated"),
        ]
        for employee_id, department_id, country, currency, salary, status in rows:
            _insert_employee(
                connection, employee_id, department_id, country, currency, salary, status
            )

    settings = _prepare(tmp_path, seed)
    body = _overview(settings, _auth(settings))
    assert body["headcount"] == 6
    assert body["total_salary_usd_scaled"] == "64000000"
    assert body["salary_usd_scale"] == 2
    assert body["average_salary_usd_scaled"] == "10666667"
    assert body["p25_salary_usd_scaled"] == "5000000"
    assert body["p50_salary_usd_scaled"] == "6500000"
    assert body["p75_salary_usd_scaled"] == "11000000"
    assert body["by_department"] == [
        {
            "department_id": 1,
            "department_name": "Engineering",
            "headcount": 3,
            "total_salary_usd_scaled": "14000000",
            "average_salary_usd_scaled": "4666667",
        },
        {
            "department_id": 2,
            "department_name": "Finance",
            "headcount": 2,
            "total_salary_usd_scaled": "20000000",
            "average_salary_usd_scaled": "10000000",
        },
        {
            "department_id": 3,
            "department_name": "Sales",
            "headcount": 1,
            "total_salary_usd_scaled": "30000000",
            "average_salary_usd_scaled": "30000000",
        },
    ]
    assert body["by_country"] == [
        {
            "country_code": "IN",
            "country_name": "India",
            "headcount": 2,
            "total_salary_usd_scaled": "17000000",
            "average_salary_usd_scaled": "8500000",
        },
        {
            "country_code": "GB",
            "country_name": "United Kingdom",
            "headcount": 1,
            "total_salary_usd_scaled": "8000000",
            "average_salary_usd_scaled": "8000000",
        },
        {
            "country_code": "US",
            "country_name": "United States",
            "headcount": 3,
            "total_salary_usd_scaled": "39000000",
            "average_salary_usd_scaled": "13000000",
        },
    ]
    # 40000 is 0–50k. 50000 is the lower edge of 50–75k. 300000 is 300k+.
    assert body["histogram"] == _histogram((1, 2, 1, 1, 0, 0, 1))
    assert "\u2013" in _HISTOGRAM_LABELS[0]
    assert "-" not in _HISTOGRAM_LABELS[0]


def test_mean_half_even(tmp_path: Path) -> None:
    # decimal_to_scaled(Decimal(sum_cents) / Decimal(100) / Decimal(count), 2)
    # Engineering: (100 + 101) / 2 = 100.5 → "100". Half-up would be "101".
    # Finance:     (101 + 102) / 2 = 101.5 → "102". Truncation would be "101".
    def seed(connection: sqlite3.Connection) -> None:
        _insert_employee(connection, "a1", 1, "US", "USD", "100")
        _insert_employee(connection, "a2", 1, "US", "USD", "101")
        _insert_employee(connection, "b1", 2, "US", "USD", "101")
        _insert_employee(connection, "b2", 2, "US", "USD", "102")

    settings = _prepare(tmp_path, seed)
    body = _overview(settings, _auth(settings))
    assert body["headcount"] == 4
    assert body["total_salary_usd_scaled"] == "404"
    assert body["average_salary_usd_scaled"] == "101"
    assert body["by_department"] == [
        {
            "department_id": 1,
            "department_name": "Engineering",
            "headcount": 2,
            "total_salary_usd_scaled": "201",
            "average_salary_usd_scaled": "100",
        },
        {
            "department_id": 2,
            "department_name": "Finance",
            "headcount": 2,
            "total_salary_usd_scaled": "203",
            "average_salary_usd_scaled": "102",
        },
    ]
    assert body["by_country"] == [
        {
            "country_code": "US",
            "country_name": "United States",
            "headcount": 4,
            "total_salary_usd_scaled": "404",
            "average_salary_usd_scaled": "101",
        }
    ]


def test_histogram_bucket_edges(tmp_path: Path) -> None:
    # Upper bounds are exclusive. 50000 is 50–75k. 300000 is 300k+.
    # A negative amount stays in 0–50k.
    salaries = (
        "-1",
        "0",
        "4999999",
        "5000000",
        "7499999",
        "7500000",
        "9999999",
        "10000000",
        "14999999",
        "15000000",
        "19999999",
        "20000000",
        "29999999",
        "30000000",
        "30000001",
    )

    def seed(connection: sqlite3.Connection) -> None:
        for index, salary in enumerate(salaries):
            _insert_employee(connection, f"e{index}", 1, "US", "USD", salary)

    settings = _prepare(tmp_path, seed)
    body = _overview(settings, _auth(settings))
    assert body["headcount"] == len(salaries)
    assert body["histogram"] == _histogram((3, 2, 2, 2, 2, 2, 2))
