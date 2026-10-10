import re
from datetime import date
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compensation import FX_SCALE, USD_SCALE
from app.directory import InvalidCursor, load_cursor, sign_cursor
from app.models import CompensationAuditLog as Audit
from app.models import Currency, Department, Employee

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_KIND = "audit"


class InvalidFilter(Exception):
    pass


def parse_iso_date(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    try:
        if _ISO_DATE.fullmatch(value) is None:
            raise ValueError(value)
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise InvalidFilter(f"invalid_date: {name} must be an ISO date (YYYY-MM-DD)") from exc


def _decode(secret: str, token: str) -> tuple[str, int]:
    payload = load_cursor(secret, token)
    created_at = payload.get("created_at")
    row_id = payload.get("id")
    if (
        payload.get("kind") != _KIND
        or not isinstance(created_at, str)
        or isinstance(row_id, bool)
        or not isinstance(row_id, int)
    ):
        raise InvalidCursor("Invalid cursor")
    return created_at, row_id


def _item(row: Any) -> dict[str, Any]:
    return {
        "id": int(row.id),
        "employee_id": row.employee_id,
        "employee_number": row.employee_number,
        "employee_name": f"{row.first_name} {row.last_name}",
        "department": {"id": int(row.department_id), "name": row.department_name},
        "previous_base_salary_scaled": row.previous_base_salary_scaled,
        "new_base_salary_scaled": row.new_base_salary_scaled,
        "previous_variable_pay_scaled": row.previous_variable_pay_scaled,
        "new_variable_pay_scaled": row.new_variable_pay_scaled,
        "salary_scale": int(row.salary_scale),
        "currency_code": row.currency_code,
        "fx_units_per_usd_scaled": row.fx_units_per_usd_scaled,
        "fx_scale": FX_SCALE,
        "previous_salary_usd_scaled": row.previous_salary_usd_scaled,
        "new_salary_usd_scaled": row.new_salary_usd_scaled,
        "salary_usd_scale": USD_SCALE,
        "reason": row.reason,
        "effective_date": row.effective_date,
        "changed_by": row.changed_by,
        "created_at": row.created_at,
    }


async def list_audit_feed(
    session: AsyncSession,
    *,
    secret: str,
    employee_id: str | None,
    department_id: int | None,
    since: str | None,
    until: str | None,
    changed_by: str | None,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    stmt = (
        select(
            Audit.id,
            Audit.employee_id,
            Employee.employee_number,
            Employee.first_name,
            Employee.last_name,
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            Audit.previous_base_salary_scaled,
            Audit.new_base_salary_scaled,
            Audit.previous_variable_pay_scaled,
            Audit.new_variable_pay_scaled,
            Currency.minor_scale.label("salary_scale"),
            Audit.currency_code,
            Audit.fx_units_per_usd_scaled,
            Audit.previous_salary_usd_scaled,
            Audit.new_salary_usd_scaled,
            Audit.reason,
            Audit.effective_date,
            Audit.changed_by,
            Audit.created_at,
        )
        .join(Employee, Employee.id == Audit.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(Currency, Currency.code == Audit.currency_code)
    )
    if employee_id:
        stmt = stmt.where(Audit.employee_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if since is not None:
        stmt = stmt.where(Audit.effective_date >= since)
    if until is not None:
        stmt = stmt.where(Audit.effective_date <= until)
    if changed_by:
        stmt = stmt.where(Audit.changed_by == changed_by)
    if cursor:
        created_at, row_id = _decode(secret, cursor)
        stmt = stmt.where(
            or_(
                Audit.created_at < created_at,
                and_(Audit.created_at == created_at, Audit.id < row_id),
            )
        )
    stmt = stmt.order_by(Audit.created_at.desc(), Audit.id.desc()).limit(limit + 1)
    fetched = (await session.execute(stmt)).all()
    rows = fetched[:limit]
    next_cursor = None
    if len(fetched) > limit:
        last = rows[-1]
        next_cursor = sign_cursor(
            secret, {"kind": _KIND, "created_at": last.created_at, "id": int(last.id)}
        )
    return {"items": [_item(row) for row in rows], "next_cursor": next_cursor}
