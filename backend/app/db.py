from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# metadata.create_all cannot create the FTS5 table or these triggers.
SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS currencies (
      code TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      minor_scale INTEGER NOT NULL,
      units_per_usd_scaled TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS countries (
      code TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      currency_code TEXT NOT NULL REFERENCES currencies(code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
      id TEXT PRIMARY KEY,
      employee_number TEXT NOT NULL UNIQUE,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      job_title TEXT NOT NULL,
      department_id INTEGER NOT NULL REFERENCES departments(id),
      country_code TEXT NOT NULL REFERENCES countries(code),
      currency_code TEXT NOT NULL REFERENCES currencies(code),
      level TEXT NOT NULL,
      base_salary_scaled TEXT NOT NULL,
      variable_pay_scaled TEXT NOT NULL,
      salary_usd_scaled TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('active', 'terminated')),
      hire_date TEXT NOT NULL,
      comp_effective_date TEXT NOT NULL,
      version_id INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS compensation_audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_id TEXT NOT NULL REFERENCES employees(id),
      previous_base_salary_scaled TEXT NOT NULL,
      new_base_salary_scaled TEXT NOT NULL,
      previous_variable_pay_scaled TEXT NOT NULL,
      new_variable_pay_scaled TEXT NOT NULL,
      currency_code TEXT NOT NULL,
      fx_units_per_usd_scaled TEXT NOT NULL,
      previous_salary_usd_scaled TEXT NOT NULL,
      new_salary_usd_scaled TEXT NOT NULL,
      reason TEXT NOT NULL,
      effective_date TEXT NOT NULL,
      changed_by TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_change_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_id TEXT NOT NULL REFERENCES employees(id),
      field TEXT NOT NULL,
      previous_value TEXT,
      new_value TEXT,
      reason TEXT NOT NULL,
      effective_date TEXT NOT NULL,
      changed_by TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS revoked_tokens (
      token_hash TEXT PRIMARY KEY,
      expires_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emp_status_dept
    ON employees(status, department_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emp_status_country
    ON employees(status, country_code)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emp_status_currency
    ON employees(status, currency_code)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emp_salary_usd
    ON employees (CAST(salary_usd_scaled AS INTEGER), id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_created
    ON compensation_audit_logs(created_at, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_change_created
    ON employee_change_logs(created_at, id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emp_base_salary
    ON employees (CAST(base_salary_scaled AS INTEGER), id)
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS employees_fts USING fts5(
      employee_number, first_name, last_name, email, job_title,
      content='employees',
      content_rowid='rowid',
      tokenize='unicode61 remove_diacritics 2'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS employees_fts_insert AFTER INSERT ON employees BEGIN
      INSERT INTO employees_fts(
        rowid, employee_number, first_name, last_name, email, job_title
      )
      VALUES (
        new.rowid, new.employee_number, new.first_name, new.last_name, new.email, new.job_title
      );
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS employees_fts_delete AFTER DELETE ON employees BEGIN
      INSERT INTO employees_fts(
        employees_fts, rowid, employee_number, first_name, last_name, email, job_title
      )
      VALUES (
        'delete',
        old.rowid, old.employee_number, old.first_name, old.last_name, old.email, old.job_title
      );
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS employees_fts_update AFTER UPDATE ON employees BEGIN
      INSERT INTO employees_fts(
        employees_fts, rowid, employee_number, first_name, last_name, email, job_title
      )
      VALUES (
        'delete',
        old.rowid, old.employee_number, old.first_name, old.last_name, old.email, old.job_title
      );
      INSERT INTO employees_fts(
        rowid, employee_number, first_name, last_name, email, job_title
      )
      VALUES (
        new.rowid, new.employee_number, new.first_name, new.last_name, new.email, new.job_title
      );
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS compensation_audit_logs_no_update
    BEFORE UPDATE ON compensation_audit_logs
    BEGIN
      SELECT RAISE(ABORT, 'audit log is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS compensation_audit_logs_no_delete
    BEFORE DELETE ON compensation_audit_logs
    BEGIN
      SELECT RAISE(ABORT, 'audit log is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS employee_change_logs_no_update
    BEFORE UPDATE ON employee_change_logs
    BEGIN
      SELECT RAISE(ABORT, 'change log is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS employee_change_logs_no_delete
    BEFORE DELETE ON employee_change_logs
    BEGIN
      SELECT RAISE(ABORT, 'change log is append-only');
    END
    """,
)


def create_db_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        # journal_mode cannot change inside a transaction.
        previous_isolation = dbapi_connection.isolation_level
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.fetchone()
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()
            dbapi_connection.isolation_level = previous_isolation

    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with factory() as session:
        yield session


async def init_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for statement in SCHEMA_STATEMENTS:
            await conn.exec_driver_sql(statement)
