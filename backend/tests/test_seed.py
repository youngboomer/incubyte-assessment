import asyncio
import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db import SCHEMA_STATEMENTS, create_db_engine, init_schema
from app.main import create_app
from app.money import decimal_to_scaled, scaled_to_decimal
from app.seed import apply_seed, generate_employees, main
from app.settings import Settings

# Pinned from Random(42). A change in draw order must fail this.
_GOLDEN_EMP_00001 = (
    "bdd640fb-0667-1ad1-1c80-317fa3b1799d",
    "kabir.johnson.1@acme.test",
    "GB",
    "United Kingdom",
    "Engineering",
    "active",
    "15350000",
    "0",
    "19679487",
)

_CURRENCIES = (
    ("AUD", "Australian Dollar", 2, "1520000", "2026-01-01T00:00:00Z"),
    ("CAD", "Canadian Dollar", 2, "1360000", "2026-01-01T00:00:00Z"),
    ("EUR", "Euro", 2, "920000", "2026-01-01T00:00:00Z"),
    ("GBP", "British Pound", 2, "780000", "2026-01-01T00:00:00Z"),
    ("INR", "Indian Rupee", 2, "83500000", "2026-01-01T00:00:00Z"),
    ("JPY", "Japanese Yen", 0, "149000000", "2026-01-01T00:00:00Z"),
    ("SGD", "Singapore Dollar", 2, "1340000", "2026-01-01T00:00:00Z"),
    ("USD", "US Dollar", 2, "1000000", "2026-01-01T00:00:00Z"),
)

_COUNTRIES = (
    ("AU", "Australia", "AUD"),
    ("CA", "Canada", "CAD"),
    ("DE", "Germany", "EUR"),
    ("GB", "United Kingdom", "GBP"),
    ("IN", "India", "INR"),
    ("JP", "Japan", "JPY"),
    ("SG", "Singapore", "SGD"),
    ("US", "United States", "USD"),
)

_DEPARTMENTS = (
    (1, "Engineering"),
    (2, "Product"),
    (3, "Sales"),
    (4, "People"),
    (5, "Finance"),
    (6, "Operations"),
)

_DIGITS = re.compile(r"^-?\d+$")

_EMPLOYEE_SQL = """
INSERT INTO employees (
  id, employee_number, first_name, last_name, email, job_title,
  department_id, country_code, currency_code, level,
  base_salary_scaled, variable_pay_scaled, salary_usd_scaled,
  status, hire_date, comp_effective_date, version_id, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_AUDIT_SQL = """
INSERT INTO compensation_audit_logs (
  employee_id, previous_base_salary_scaled, new_base_salary_scaled,
  previous_variable_pay_scaled, new_variable_pay_scaled, currency_code,
  fx_units_per_usd_scaled, previous_salary_usd_scaled, new_salary_usd_scaled,
  reason, effective_date, changed_by, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def _employee_tuple(
    employee_id: str,
    employee_number: str,
    email: str,
    salary_usd_scaled: str,
) -> tuple[object, ...]:
    return (
        employee_id,
        employee_number,
        "Ada",
        "Okoye",
        email,
        "Software Engineer",
        1,
        "US",
        "USD",
        "IC3",
        "0",
        "0",
        salary_usd_scaled,
        "active",
        "2021-03-15",
        "2021-03-15",
        1,
        "2021-03-15T00:00:00Z",
        "2021-03-15T00:00:00Z",
    )


def test_generate_employees_honors_count() -> None:
    assert generate_employees(0) == []
    with pytest.raises(ValueError, match="count must be >= 0"):
        generate_employees(-1)

    rows = generate_employees(5)
    assert rows == generate_employees(5)
    assert generate_employees(4) == rows[:4]
    assert [row.employee_number for row in rows] == [
        "EMP-00001",
        "EMP-00002",
        "EMP-00003",
        "EMP-00004",
        "EMP-00005",
    ]
    for number, row in enumerate(rows, start=1):
        assert row.email == f"{row.first_name}.{row.last_name}.{number}@acme.test".lower()
        assert row.email == row.email.lower()
        assert row.comp_effective_date == row.hire_date
        assert row.created_at == f"{row.hire_date}T00:00:00Z"
        assert row.updated_at == row.created_at
        assert "2016-01-01" <= row.hire_date <= "2025-12-31"
        assert _DIGITS.fullmatch(row.base_salary_scaled)
        assert _DIGITS.fullmatch(row.variable_pay_scaled)
        assert _DIGITS.fullmatch(row.salary_usd_scaled)


def test_cli_count_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "cli.db"
    monkeypatch.setenv("DATABASE_URL", _sqlite_url(db_path))
    monkeypatch.setenv("SEED_COUNT", "7")

    main(["--count", "5"])
    main(["--count", "5"])

    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone() == (5,)
        numbers = connection.execute(
            "SELECT employee_number FROM employees ORDER BY employee_number"
        ).fetchall()
        assert numbers == [(f"EMP-{number:05d}",) for number in range(1, 6)]
        currencies, countries, departments = _reference_rows(connection)
        assert tuple(currencies) == _CURRENCIES
        assert tuple(countries) == _COUNTRIES
        assert tuple(departments) == _DEPARTMENTS
    finally:
        connection.close()

    monkeypatch.setenv("SEED_COUNT", "5")
    untouched = tmp_path / "default.db"
    monkeypatch.setenv("DATABASE_URL", _sqlite_url(untouched))
    main([])
    connection = sqlite3.connect(untouched)
    try:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone() == (5,)
    finally:
        connection.close()


def test_reset_replaces_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "reset.db"
    monkeypatch.setenv("DATABASE_URL", _sqlite_url(db_path))
    main(["--count", "5"])
    expected = generate_employees(5)

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        employee_id = connection.execute(
            "SELECT id FROM employees WHERE employee_number = 'EMP-00001'"
        ).fetchone()[0]
        connection.execute(
            "UPDATE employees SET first_name = 'Tampered' WHERE employee_number = 'EMP-00001'"
        )
        connection.execute(
            _EMPLOYEE_SQL,
            _employee_tuple("extra-employee", "EMP-99999", "extra.person.99999@acme.test", "100"),
        )
        connection.execute(
            "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
            "VALUES ('XXX', 'Extra', 2, '1000000', '2026-01-01T00:00:00Z')"
        )
        connection.execute(_AUDIT_SQL, _audit_params(employee_id))
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone() == (6,)
        assert connection.execute("SELECT COUNT(*) FROM compensation_audit_logs").fetchone() == (1,)
    finally:
        connection.close()

    main(["--count", "5", "--reset"])

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT employee_number, email, first_name FROM employees ORDER BY employee_number"
        ).fetchall()
        assert rows == [
            (row.employee_number, row.email, row.first_name) for row in expected
        ]
        assert connection.execute(
            "SELECT COUNT(*) FROM employees WHERE employee_number = 'EMP-99999'"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT first_name FROM employees WHERE employee_number = 'EMP-00001'"
        ).fetchone() != ("Tampered",)
        assert connection.execute("SELECT COUNT(*) FROM compensation_audit_logs").fetchone() == (0,)
        currencies, countries, departments = _reference_rows(connection, skip_currency="XXX")
        assert tuple(currencies) == _CURRENCIES
        assert tuple(countries) == _COUNTRIES
        assert tuple(departments) == _DEPARTMENTS
        assert connection.execute(
            "SELECT code FROM currencies WHERE code = 'XXX'"
        ).fetchone() == ("XXX",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND name = 'compensation_audit_logs_no_delete'"
        ).fetchone() == ("compensation_audit_logs_no_delete",)

        kept_id = connection.execute(
            "SELECT id FROM employees WHERE employee_number = 'EMP-00001'"
        ).fetchone()[0]
        connection.execute(_AUDIT_SQL, _audit_params(kept_id))
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM compensation_audit_logs")
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM compensation_audit_logs").fetchone() == (1,)
    finally:
        connection.close()


def test_startup_seeds_empty_database_once(tmp_path: Path) -> None:
    expected = [(row.employee_number, row.email) for row in generate_employees(5)]
    db_path = tmp_path / "startup.db"
    url = _sqlite_url(db_path)
    for _ in range(2):
        app = create_app(Settings(database_url=url, seed_count=5))
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT employee_number, email FROM employees ORDER BY employee_number"
        ).fetchall()
    finally:
        connection.close()
    assert rows == expected


def test_startup_seed_count_zero_inserts_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "zero.db"
    app = create_app(Settings(database_url=_sqlite_url(db_path), seed_count=0))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM currencies").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM countries").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM departments").fetchone() == (0,)
    finally:
        connection.close()


def test_startup_does_not_reseed_existing_employees(tmp_path: Path) -> None:
    db_path = tmp_path / "existing.db"
    url = _sqlite_url(db_path)

    async def _prepare() -> None:
        engine = create_db_engine(url)
        try:
            await init_schema(engine)
            async with engine.begin() as conn:
                await conn.exec_driver_sql(
                    "INSERT INTO currencies "
                    "(code, name, minor_scale, units_per_usd_scaled, updated_at) "
                    "VALUES ('USD', 'US Dollar', 2, '1000000', '2026-01-01T00:00:00Z')"
                )
                await conn.exec_driver_sql(
                    "INSERT INTO countries (code, name, currency_code) "
                    "VALUES ('US', 'United States', 'USD')"
                )
                await conn.exec_driver_sql(
                    "INSERT INTO departments (id, name) VALUES (1, 'Engineering')"
                )
                await conn.exec_driver_sql(
                    """
                    INSERT INTO employees (
                      id, employee_number, first_name, last_name, email, job_title,
                      department_id, country_code, currency_code, level,
                      base_salary_scaled, variable_pay_scaled, salary_usd_scaled,
                      status, hire_date, comp_effective_date, version_id,
                      created_at, updated_at
                    ) VALUES (
                      'keep-me', 'EMP-00999', 'Keep', 'Me', 'keep.me.999@acme.test',
                      'Software Engineer', 1, 'US', 'USD', 'IC2',
                      '100', '0', '100', 'active', '2020-01-01', '2020-01-01', 1,
                      '2020-01-01T00:00:00Z', '2020-01-01T00:00:00Z'
                    )
                    """
                )
        finally:
            await engine.dispose()

    asyncio.run(_prepare())
    app = create_app(Settings(database_url=url, seed_count=5))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute(
            "SELECT employee_number, email FROM employees"
        ).fetchall() == [("EMP-00999", "keep.me.999@acme.test")]
    finally:
        connection.close()


def test_seed_ten_thousand_golden_row_and_invariants(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path / "tenk.db")

    async def _run() -> None:
        engine = create_db_engine(url)
        try:
            await init_schema(engine)
            inserted = await apply_seed(engine, 10_000, reset=False)
            assert inserted == 10_000
            async with engine.connect() as conn:
                await _assert_ten_thousand(conn)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_salary_usd_scaled_orders_99_before_100(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "sort.db")
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
            "VALUES ('USD', 'US Dollar', 2, '1000000', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO countries (code, name, currency_code) "
            "VALUES ('US', 'United States', 'USD')"
        )
        connection.execute("INSERT INTO departments (id, name) VALUES (1, 'Engineering')")
        connection.execute(
            _EMPLOYEE_SQL,
            _employee_tuple("salary-100", "EMP-00100", "high.salary.100@acme.test", "100"),
        )
        connection.execute(
            _EMPLOYEE_SQL,
            _employee_tuple("salary-99", "EMP-00099", "low.salary.99@acme.test", "99"),
        )
        connection.commit()
        ordered = connection.execute(
            "SELECT salary_usd_scaled FROM employees "
            "ORDER BY CAST(salary_usd_scaled AS INTEGER)"
        ).fetchall()
        assert [row[0] for row in ordered] == ["99", "100"]
    finally:
        connection.close()


async def _assert_ten_thousand(conn: AsyncConnection) -> None:
    total = int((await conn.exec_driver_sql("SELECT COUNT(*) FROM employees")).scalar_one())
    assert total == 10_000

    golden = (
        await conn.exec_driver_sql(
            """
            SELECT e.id, e.email, e.country_code, c.name, d.name, e.status,
                   e.base_salary_scaled, e.variable_pay_scaled, e.salary_usd_scaled
            FROM employees e
            JOIN countries c ON c.code = e.country_code
            JOIN departments d ON d.id = e.department_id
            WHERE e.employee_number = 'EMP-00001'
            """
        )
    ).one()
    assert tuple(golden) == _GOLDEN_EMP_00001

    pay_rows = (
        await conn.exec_driver_sql(
            """
            SELECT e.base_salary_scaled, e.variable_pay_scaled, e.salary_usd_scaled,
                   c.minor_scale, c.units_per_usd_scaled
            FROM employees e
            JOIN currencies c ON c.code = e.currency_code
            """
        )
    ).all()
    assert len(pay_rows) == 10_000
    for base, variable, usd, scale, rate in pay_rows:
        assert _DIGITS.fullmatch(base)
        assert _DIGITS.fullmatch(variable)
        assert _DIGITS.fullmatch(usd)
        local = scaled_to_decimal(base, scale) + scaled_to_decimal(variable, scale)
        expected = decimal_to_scaled(local / scaled_to_decimal(rate, 6), 2)
        assert usd == expected

    status_counts = dict(
        (await conn.exec_driver_sql("SELECT status, COUNT(*) FROM employees GROUP BY status")).all()
    )
    terminated = int(status_counts["terminated"])
    assert 0.03 <= terminated / 10_000 <= 0.05

    departments = dict(
        (
            await conn.exec_driver_sql(
                """
                SELECT d.name, COUNT(*)
                FROM employees e
                JOIN departments d ON d.id = e.department_id
                GROUP BY d.name
                """
            )
        ).all()
    )
    engineering = int(departments["Engineering"])
    assert engineering > max(count for name, count in departments.items() if name != "Engineering")

    countries = dict(
        (
            await conn.exec_driver_sql(
                """
                SELECT c.name, COUNT(*)
                FROM employees e
                JOIN countries c ON c.code = e.country_code
                GROUP BY c.name
                """
            )
        ).all()
    )
    heaviest = {"India", "United States"}
    others = [int(count) for name, count in countries.items() if name not in heaviest]
    assert int(countries["India"]) > max(others)
    assert int(countries["United States"]) > max(others)

    levels = dict(
        (await conn.exec_driver_sql("SELECT level, COUNT(*) FROM employees GROUP BY level")).all()
    )
    rest = [int(count) for name, count in levels.items() if name not in {"IC2", "IC3"}]
    assert int(levels["IC2"]) > max(rest)
    assert int(levels["IC3"]) > max(rest)
    assert int(levels["M2"]) < min(int(count) for name, count in levels.items() if name != "M2")

    sales_zero, other_nonzero, sales_count = (
        await conn.exec_driver_sql(
            """
            SELECT
              SUM(CASE WHEN d.name = 'Sales' AND e.variable_pay_scaled = '0' THEN 1 ELSE 0 END),
              SUM(CASE WHEN d.name != 'Sales' AND e.variable_pay_scaled != '0' THEN 1 ELSE 0 END),
              SUM(CASE WHEN d.name = 'Sales' THEN 1 ELSE 0 END)
            FROM employees e
            JOIN departments d ON d.id = e.department_id
            """
        )
    ).one()
    assert int(sales_count) > 0
    assert int(sales_zero) == 0
    assert int(other_nonzero) == 0

    matched = (
        await conn.exec_driver_sql(
            "SELECT employee_number FROM employees_fts WHERE employees_fts MATCH 'johnson'"
        )
    ).all()
    assert any(row[0] == "EMP-00001" for row in matched)


def _reference_rows(
    connection: sqlite3.Connection,
    *,
    skip_currency: str | None = None,
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]], list[tuple[object, ...]]]:
    currency_sql = (
        "SELECT code, name, minor_scale, units_per_usd_scaled, updated_at FROM currencies"
    )
    params: tuple[object, ...] = ()
    if skip_currency is not None:
        currency_sql += " WHERE code != ?"
        params = (skip_currency,)
    currencies = connection.execute(currency_sql + " ORDER BY code", params).fetchall()
    countries = connection.execute(
        "SELECT code, name, currency_code FROM countries ORDER BY code"
    ).fetchall()
    departments = connection.execute("SELECT id, name FROM departments ORDER BY id").fetchall()
    return currencies, countries, departments


def _audit_params(employee_id: str) -> tuple[str, ...]:
    return (
        employee_id,
        "100",
        "200",
        "0",
        "0",
        "USD",
        "1000000",
        "100",
        "200",
        "Annual review",
        "2024-01-01",
        "hr@acme.test",
        "2024-01-01T00:00:00Z",
    )


