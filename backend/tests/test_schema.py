import asyncio
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from app.db import create_db_engine, init_schema
from app.models import Base

_EMPLOYEE_SQL = """
INSERT INTO employees (
  id, employee_number, first_name, last_name, email, job_title,
  department_id, country_code, currency_code, level,
  base_salary_scaled, variable_pay_scaled, salary_usd_scaled,
  status, hire_date, comp_effective_date, version_id, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_MONEY_COLUMNS = {
    "currencies": ["units_per_usd_scaled"],
    "employees": ["base_salary_scaled", "variable_pay_scaled", "salary_usd_scaled"],
    "compensation_audit_logs": [
        "previous_base_salary_scaled",
        "new_base_salary_scaled",
        "previous_variable_pay_scaled",
        "new_variable_pay_scaled",
        "fx_units_per_usd_scaled",
        "previous_salary_usd_scaled",
        "new_salary_usd_scaled",
    ],
}


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def test_pragmas_schema_and_foreign_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "comppulse.db"
    engine = create_db_engine(_sqlite_url(db_path))
    assert isinstance(engine.sync_engine.pool, NullPool)

    async def _run() -> None:
        await init_schema(engine)
        await init_schema(engine)
        async with engine.connect() as conn:
            foreign_keys = (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar_one()
            journal_mode = (await conn.exec_driver_sql("PRAGMA journal_mode")).scalar_one()
            busy_timeout = (await conn.exec_driver_sql("PRAGMA busy_timeout")).scalar_one()
            synchronous = (await conn.exec_driver_sql("PRAGMA synchronous")).scalar_one()
            assert foreign_keys == 1
            assert str(journal_mode).lower() == "wal"
            assert busy_timeout == 5000
            assert synchronous == 1
            await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
        with pytest.raises(IntegrityError):
            async with engine.begin() as conn:
                await conn.exec_driver_sql(
                    "INSERT INTO countries (code, name, currency_code) "
                    "VALUES ('US', 'United States', 'NOPE')"
                )
        await engine.dispose()

    asyncio.run(_run())
    _assert_catalog(db_path)
    _assert_fts_and_audit(db_path)


def test_models_match_schema_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "models.db"
    engine = create_db_engine(_sqlite_url(db_path))

    async def _run() -> None:
        await init_schema(engine)
        await engine.dispose()

    asyncio.run(_run())
    connection = sqlite3.connect(db_path)
    try:
        for table_name, table in Base.metadata.tables.items():
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            assert [row[1] for row in rows] == [column.name for column in table.columns]
            declared = {row[1]: row[2].upper() for row in rows}
            for column_name in _MONEY_COLUMNS.get(table_name, []):
                assert declared[column_name] == "TEXT"
                assert str(table.c[column_name].type) == "TEXT"
    finally:
        connection.close()


def _assert_catalog(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        objects = {
            (row[0], row[1]): row[2]
            for row in connection.execute(
                "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            )
        }
        names = {name for _, name in objects}
        assert {
            "currencies",
            "countries",
            "departments",
            "employees",
            "compensation_audit_logs",
            "employees_fts",
            "idx_emp_status_dept",
            "idx_emp_status_country",
            "idx_emp_status_currency",
            "idx_emp_salary_usd",
            "idx_emp_base_salary",
            "employees_fts_insert",
            "employees_fts_delete",
            "employees_fts_update",
            "compensation_audit_logs_no_update",
            "compensation_audit_logs_no_delete",
        } <= names
        employee_sql = objects[("table", "employees")] or ""
        assert "WITHOUT ROWID" not in employee_sql.upper()
        salary_index = objects[("index", "idx_emp_salary_usd")] or ""
        assert "CAST(salary_usd_scaled AS INTEGER)" in salary_index
        fts_sql = objects[("table", "employees_fts")] or ""
        assert "unicode61 remove_diacritics 2" in fts_sql
    finally:
        connection.close()


def _assert_fts_and_audit(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute(
            "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
            "VALUES ('USD', 'US Dollar', 2, '1000000', '2026-01-01T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO countries (code, name, currency_code) "
            "VALUES ('US', 'United States', 'USD')"
        )
        connection.execute("INSERT INTO departments (id, name) VALUES (1, 'Engineering')")
        _insert_employee(
            connection, "emp-1", "EMP-00001", "José", "Okoye", "ada.1@acme.test"
        )
        assert _match(connection, "jose") == ["EMP-00001"]
        assert _match(connection, "okoye") == ["EMP-00001"]

        connection.execute("UPDATE employees SET last_name = 'Ng' WHERE id = 'emp-1'")
        assert _match(connection, "okoye") == []
        assert _match(connection, "ng") == ["EMP-00001"]

        connection.execute("DELETE FROM employees WHERE id = 'emp-1'")
        assert _match(connection, "ng") == []

        _insert_employee(
            connection,
            "emp-2",
            "EMP-00002",
            "Ada",
            "Lovelace",
            "ada.lovelace.2@acme.test",
        )
        connection.execute(
            """
            INSERT INTO compensation_audit_logs (
              employee_id, previous_base_salary_scaled, new_base_salary_scaled,
              previous_variable_pay_scaled, new_variable_pay_scaled, currency_code,
              fx_units_per_usd_scaled, previous_salary_usd_scaled, new_salary_usd_scaled,
              reason, effective_date, changed_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "emp-2",
                "15500000",
                "16000000",
                "0",
                "0",
                "USD",
                "1000000",
                "15500000",
                "16000000",
                "Annual review",
                "2026-04-01",
                "hr@acme.test",
                "2026-04-01T09:00:00Z",
            ),
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE compensation_audit_logs SET reason = 'changed'")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM compensation_audit_logs")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO employees ("
                "id, employee_number, first_name, last_name, email, job_title, "
                "department_id, country_code, currency_code, level, "
                "base_salary_scaled, variable_pay_scaled, salary_usd_scaled, "
                "status, hire_date, comp_effective_date, created_at, updated_at"
                ") VALUES ("
                "'emp-3', 'EMP-00003', 'A', 'B', 'a.b.3@acme.test', 'Role', "
                "1, 'US', 'USD', 'IC1', '1', '0', '1', 'nope', "
                "'2026-01-01', '2026-01-01', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
            )
        connection.rollback()
        assert connection.execute("SELECT COUNT(*) FROM compensation_audit_logs").fetchone() == (1,)
    finally:
        connection.close()


def _insert_employee(
    connection: sqlite3.Connection,
    employee_id: str,
    employee_number: str,
    first_name: str,
    last_name: str,
    email: str,
) -> None:
    connection.execute(
        _EMPLOYEE_SQL,
        (
            employee_id,
            employee_number,
            first_name,
            last_name,
            email,
            "Software Engineer",
            1,
            "US",
            "USD",
            "IC3",
            "15500000",
            "0",
            "15500000",
            "active",
            "2021-03-15",
            "2025-04-01",
            1,
            "2021-03-15T00:00:00Z",
            "2025-04-01T00:00:00Z",
        ),
    )


def _match(connection: sqlite3.Connection, query: str) -> list[str]:
    rows = connection.execute(
        "SELECT employee_number FROM employees_fts WHERE employees_fts MATCH ?",
        (query,),
    ).fetchall()
    return [row[0] for row in rows]
