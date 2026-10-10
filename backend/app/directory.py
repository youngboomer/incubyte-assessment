import csv
import io
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from itsdangerous import BadData, URLSafeSerializer
from sqlalchemy import (
    Integer,
    and_,
    bindparam,
    cast,
    column,
    func,
    literal_column,
    or_,
    select,
    table,
    text,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.models import Country, Currency, Department, Employee
from app.money import scaled_to_decimal
from app.search import sanitize_fts_query

CURSOR_SALT = "comppulse-cursor"
SALARY_USD_SCALE = 2
UNITS_PER_USD_SCALE = 6
LEVELS = ("IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2")
STATUSES = ("active", "terminated")
_SALARY_SORTS = frozenset({"base_salary", "salary_usd"})
_CSV_HEADERS = (
    "employee number",
    "name",
    "email",
    "title",
    "department",
    "country",
    "currency",
    "level",
    "base major",
    "variable major",
    "USD major",
    "status",
)
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_FTS = table("employees_fts", column("rowid"))


class InvalidCursor(Exception):
    pass


class InvalidFilter(Exception):
    pass


def parse_salary_usd_bound(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        if not (value.isascii() and value.isdigit()):
            raise ValueError(value)
        scaled_to_decimal(value, 0)
    except ValueError as exc:
        raise InvalidFilter("invalid_salary_bound: expected non-negative int64 digits") from exc
    return int(value)


def _serializer(secret: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret, salt=CURSOR_SALT)


def sign_cursor(secret: str, payload: dict[str, Any]) -> str:
    return _serializer(secret).dumps(payload)


def load_cursor(secret: str, token: str) -> dict[str, Any]:
    try:
        payload = _serializer(secret).loads(token)
    except BadData as exc:
        raise InvalidCursor("Invalid cursor") from exc
    if not isinstance(payload, dict):
        raise InvalidCursor("Invalid cursor")
    return payload


def _sort_columns(sort: str) -> tuple[ColumnElement[Any], ...]:
    employee_id = Employee.id
    columns: dict[str, tuple[ColumnElement[Any], ...]] = {
        "name": (Employee.last_name, Employee.first_name, employee_id),
        "employee_number": (Employee.employee_number, employee_id),
        "department": (Department.name, employee_id),
        "country": (Country.name, employee_id),
        "title": (Employee.job_title, employee_id),
        # Text order would place "100" before "99".
        "base_salary": (cast(Employee.base_salary_scaled, Integer), employee_id),
        "salary_usd": (cast(Employee.salary_usd_scaled, Integer), employee_id),
        "hire_date": (Employee.hire_date, employee_id),
    }
    try:
        return columns[sort]
    except KeyError as exc:
        raise ValueError(sort) from exc


def _boundary_values(sort: str, row: Any) -> list[str]:
    if sort == "name":
        raw: Sequence[Any] = (row.last_name, row.first_name)
    elif sort == "employee_number":
        raw = (row.employee_number,)
    elif sort == "department":
        raw = (row.department_name,)
    elif sort == "country":
        raw = (row.country_name,)
    elif sort == "title":
        raw = (row.job_title,)
    elif sort == "base_salary":
        raw = (row.base_salary_scaled,)
    elif sort == "salary_usd":
        raw = (row.salary_usd_scaled,)
    elif sort == "hire_date":
        raw = (row.hire_date,)
    else:
        raise ValueError(sort)
    return [str(value) for value in raw]


def _encode_cursor(secret: str, sort: str, direction: str, row: Any, side: str) -> str:
    payload = {
        "sort": sort,
        "direction": direction,
        "values": _boundary_values(sort, row),
        "id": row.id,
        "side": side,
    }
    return _serializer(secret).dumps(payload)


def _decode_cursor(secret: str, token: str, *, sort: str, direction: str) -> dict[str, Any]:
    try:
        payload = _serializer(secret).loads(token)
    except BadData as exc:
        raise InvalidCursor("Invalid cursor") from exc
    if not isinstance(payload, dict):
        raise InvalidCursor("Invalid cursor")
    if payload.get("sort") != sort or payload.get("direction") != direction:
        raise InvalidCursor("Cursor does not match sort or direction")
    values = payload.get("values")
    row_id = payload.get("id")
    side = payload.get("side")
    if side not in {"next", "prev"} or not isinstance(row_id, str) or not isinstance(values, list):
        raise InvalidCursor("Invalid cursor")
    if len(values) != len(_sort_columns(sort)) - 1 or not all(isinstance(v, str) for v in values):
        raise InvalidCursor("Invalid cursor")
    return {"values": values, "id": row_id, "side": side}


def _base_select() -> Select[Any]:
    return (
        select(
            Employee.id.label("id"),
            Employee.employee_number.label("employee_number"),
            Employee.first_name.label("first_name"),
            Employee.last_name.label("last_name"),
            Employee.email.label("email"),
            Employee.job_title.label("job_title"),
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            Country.code.label("country_code"),
            Country.name.label("country_name"),
            Employee.currency_code.label("currency_code"),
            Employee.level.label("level"),
            Employee.base_salary_scaled.label("base_salary_scaled"),
            Employee.variable_pay_scaled.label("variable_pay_scaled"),
            Currency.minor_scale.label("salary_scale"),
            Employee.salary_usd_scaled.label("salary_usd_scaled"),
            Employee.status.label("status"),
            Employee.hire_date.label("hire_date"),
            Employee.comp_effective_date.label("comp_effective_date"),
            Employee.version_id.label("version_id"),
        )
        .join(Department, Department.id == Employee.department_id)
        .join(Country, Country.code == Employee.country_code)
        .join(Currency, Currency.code == Employee.currency_code)
    )


def _fts_clause(match_query: str) -> ColumnElement[bool]:
    # MATCH names the FTS table. SQLite rejects a SQL alias in that position.
    rowids = (
        select(_FTS.c.rowid)
        .where(text("employees_fts MATCH :fts_query").bindparams(fts_query=match_query))
        .correlate(None)
    )
    return literal_column("employees.rowid").in_(rowids)


def _apply_filters(
    stmt: Select[Any],
    *,
    q: str | None,
    department_id: int | None,
    country: str | None,
    currency: str | None,
    status: str | None,
    level: str | None = None,
    salary_usd_min: int | None = None,
    salary_usd_max: int | None = None,
) -> Select[Any]:
    clauses: list[ColumnElement[bool]] = []
    if department_id is not None:
        clauses.append(Employee.department_id == department_id)
    if country:
        clauses.append(Employee.country_code == country)
    if currency:
        clauses.append(Employee.currency_code == currency)
    if status:
        clauses.append(Employee.status == status)
    if level:
        clauses.append(Employee.level == level)
    if salary_usd_min is not None:
        clauses.append(cast(Employee.salary_usd_scaled, Integer) >= salary_usd_min)
    if salary_usd_max is not None:
        clauses.append(cast(Employee.salary_usd_scaled, Integer) <= salary_usd_max)
    if q:
        match_query = sanitize_fts_query(q)
        if match_query is not None:
            clauses.append(_fts_clause(match_query))
    if clauses:
        stmt = stmt.where(*clauses)
    return stmt


def _wants_greater(direction: str, side: str) -> bool:
    # Ascending next and descending prev both sit on the greater side of the tuple.
    if direction == "asc":
        return side == "next"
    return side == "prev"


def _salary_seek_predicate(
    columns: Sequence[ColumnElement[Any]],
    values: Sequence[str],
    row_id: str,
    direction: str,
    side: str,
) -> ColumnElement[bool]:
    """Expand a salary comparison so SQLite can seek the expression index.

    ``(CAST(salary AS INTEGER), id) > (?, ?)`` is planned as a rewind of
    ``idx_emp_salary_usd``. The same comparison written as
    ``salary >= ? AND (salary > ? OR id > ?)`` is a SeekGE on that index.
    """
    salary = columns[0]
    identity = columns[1]
    bound = cast(bindparam("cv0", values[0]), Integer)
    row = bindparam("cid", row_id)
    if _wants_greater(direction, side):
        return and_(salary >= bound, or_(salary > bound, identity > row))
    return and_(salary <= bound, or_(salary < bound, identity < row))


def _seek_predicate(
    columns: Sequence[ColumnElement[Any]],
    sort: str,
    values: Sequence[str],
    row_id: str,
    direction: str,
    side: str,
) -> ColumnElement[bool]:
    if sort in _SALARY_SORTS:
        return _salary_seek_predicate(columns, values, row_id, direction, side)
    right: list[ColumnElement[Any]] = [
        bindparam(f"cv{index}", value) for index, value in enumerate(values)
    ]
    right.append(bindparam("cid", row_id))
    left = tuple_(*columns)
    other = tuple_(*right)
    if _wants_greater(direction, side):
        return left > other
    return left < other


def _order_by(
    columns: Sequence[ColumnElement[Any]], direction: str, *, reverse: bool
) -> list[ColumnElement[Any]]:
    descending = direction == "desc"
    if reverse:
        descending = not descending
    if descending:
        return [expression.desc() for expression in columns]
    return [expression.asc() for expression in columns]


def _employee_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "employee_number": row.employee_number,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "email": row.email,
        "job_title": row.job_title,
        "department": {"id": int(row.department_id), "name": row.department_name},
        "country": {"code": row.country_code, "name": row.country_name},
        "currency_code": row.currency_code,
        "level": row.level,
        "base_salary_scaled": row.base_salary_scaled,
        "variable_pay_scaled": row.variable_pay_scaled,
        "salary_scale": int(row.salary_scale),
        "salary_usd_scaled": row.salary_usd_scaled,
        "salary_usd_scale": SALARY_USD_SCALE,
        "status": row.status,
        "hire_date": row.hire_date,
        "comp_effective_date": row.comp_effective_date,
        "version_id": int(row.version_id),
    }


async def _count(
    session: AsyncSession,
    *,
    q: str | None,
    department_id: int | None,
    country: str | None,
    currency: str | None,
    status: str | None,
    level: str | None,
    salary_usd_min: int | None,
    salary_usd_max: int | None,
) -> int:
    stmt = _apply_filters(
        select(func.count()).select_from(Employee),
        q=q,
        department_id=department_id,
        country=country,
        currency=currency,
        status=status,
        level=level,
        salary_usd_min=salary_usd_min,
        salary_usd_max=salary_usd_max,
    )
    return int((await session.execute(stmt)).scalar_one())


async def _exists_beyond(
    session: AsyncSession,
    row: Any,
    *,
    sort: str,
    direction: str,
    side: str,
    q: str | None,
    department_id: int | None,
    country: str | None,
    currency: str | None,
    status: str | None,
    level: str | None,
    salary_usd_min: int | None,
    salary_usd_max: int | None,
) -> bool:
    columns = _sort_columns(sort)
    stmt = _apply_filters(
        _base_select(),
        q=q,
        department_id=department_id,
        country=country,
        currency=currency,
        status=status,
        level=level,
        salary_usd_min=salary_usd_min,
        salary_usd_max=salary_usd_max,
    )
    stmt = stmt.where(
        _seek_predicate(columns, sort, _boundary_values(sort, row), row.id, direction, side)
    ).limit(1)
    return (await session.execute(stmt)).first() is not None


async def list_employees(
    session: AsyncSession,
    *,
    secret: str,
    q: str | None,
    department_id: int | None,
    country: str | None,
    currency: str | None,
    status: str | None,
    level: str | None,
    salary_usd_min: int | None,
    salary_usd_max: int | None,
    sort: str,
    direction: str,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    payload = (
        _decode_cursor(secret, cursor, sort=sort, direction=direction) if cursor else None
    )
    columns = _sort_columns(sort)
    reverse = payload is not None and payload["side"] == "prev"
    filters = {
        "q": q,
        "department_id": department_id,
        "country": country,
        "currency": currency,
        "status": status,
        "level": level,
        "salary_usd_min": salary_usd_min,
        "salary_usd_max": salary_usd_max,
    }
    stmt = _apply_filters(_base_select(), **filters)
    if payload is not None:
        stmt = stmt.where(
            _seek_predicate(
                columns,
                sort,
                payload["values"],
                payload["id"],
                direction,
                payload["side"],
            )
        )
    stmt = stmt.order_by(*_order_by(columns, direction, reverse=reverse)).limit(limit + 1)
    fetched = (await session.execute(stmt)).all()
    has_more = len(fetched) > limit
    rows = list(fetched[:limit])
    if reverse:
        rows.reverse()

    next_cursor = None
    prev_cursor = None
    if rows:
        forward = payload is None or payload["side"] == "next"
        if forward:
            if has_more:
                next_cursor = _encode_cursor(secret, sort, direction, rows[-1], "next")
            if payload is not None and await _exists_beyond(
                session, rows[0], sort=sort, direction=direction, side="prev", **filters
            ):
                prev_cursor = _encode_cursor(secret, sort, direction, rows[0], "prev")
        else:
            if has_more:
                prev_cursor = _encode_cursor(secret, sort, direction, rows[0], "prev")
            if await _exists_beyond(
                session, rows[-1], sort=sort, direction=direction, side="next", **filters
            ):
                next_cursor = _encode_cursor(secret, sort, direction, rows[-1], "next")

    return {
        "items": [_employee_dict(row) for row in rows],
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
        "total": await _count(session, **filters),
    }


async def get_employee(session: AsyncSession, employee_id: str) -> dict[str, Any] | None:
    row = (await session.execute(_base_select().where(Employee.id == employee_id))).one_or_none()
    if row is None:
        return None
    return _employee_dict(row)


def _major_units(scaled: str, scale: int) -> str:
    # Decimal division normalizes "120000.50" to "120000.5". Keep the currency scale.
    amount = scaled_to_decimal(scaled, scale).quantize(Decimal(1).scaleb(-scale))
    return str(amount)


def _csv_text(value: str) -> str:
    return f"'{value}" if value.startswith(_CSV_FORMULA_PREFIXES) else value


def _render_csv(rows: Sequence[Any]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_HEADERS)
    for row in rows:
        scale = int(row.salary_scale)
        writer.writerow(
            [
                _csv_text(row.employee_number),
                _csv_text(f"{row.first_name} {row.last_name}"),
                _csv_text(row.email),
                _csv_text(row.job_title),
                _csv_text(row.department_name),
                _csv_text(row.country_name),
                row.currency_code,
                row.level,
                _major_units(row.base_salary_scaled, scale),
                _major_units(row.variable_pay_scaled, scale),
                _major_units(row.salary_usd_scaled, SALARY_USD_SCALE),
                row.status,
            ]
        )
    return buffer.getvalue()


async def export_employees_csv(
    session: AsyncSession,
    *,
    q: str | None,
    department_id: int | None,
    country: str | None,
    currency: str | None,
    status: str | None,
    level: str | None,
    salary_usd_min: int | None,
    salary_usd_max: int | None,
    sort: str,
    direction: str,
) -> str:
    stmt = _apply_filters(
        _base_select(),
        q=q,
        department_id=department_id,
        country=country,
        currency=currency,
        status=status,
        level=level,
        salary_usd_min=salary_usd_min,
        salary_usd_max=salary_usd_max,
    )
    stmt = stmt.order_by(*_order_by(_sort_columns(sort), direction, reverse=False))
    rows = (await session.execute(stmt)).all()
    return _render_csv(rows)


async def fetch_reference(session: AsyncSession) -> dict[str, Any]:
    departments = (
        await session.execute(select(Department.id, Department.name).order_by(Department.id))
    ).all()
    countries = (
        await session.execute(
            select(Country.code, Country.name, Country.currency_code).order_by(Country.code)
        )
    ).all()
    currencies = (
        await session.execute(
            select(
                Currency.code,
                Currency.name,
                Currency.minor_scale,
                Currency.units_per_usd_scaled,
            ).order_by(Currency.code)
        )
    ).all()
    return {
        "departments": [{"id": int(row.id), "name": row.name} for row in departments],
        "countries": [
            {"code": row.code, "name": row.name, "currency_code": row.currency_code}
            for row in countries
        ],
        "currencies": [
            {
                "code": row.code,
                "name": row.name,
                "minor_scale": int(row.minor_scale),
                "units_per_usd_scaled": row.units_per_usd_scaled,
                "units_per_usd_scale": UNITS_PER_USD_SCALE,
            }
            for row in currencies
        ],
        "levels": list(LEVELS),
        "statuses": list(STATUSES),
    }
