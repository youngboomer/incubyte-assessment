from typing import Any

from sqlalchemy import Integer, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.audit_feed import InvalidFilter
from app.directory import InvalidCursor, load_cursor, sign_cursor
from app.models import Department, Employee
from app.models import EmployeeChangeLog as Change

_KIND = "changes"
_DEPARTMENT_FIELD = "department_id"
FIELDS = (
    "first_name",
    "last_name",
    "email",
    "job_title",
    _DEPARTMENT_FIELD,
    "level",
    "status",
)


def validate_field(field: str | None) -> str | None:
    if field is not None and field not in FIELDS:
        raise InvalidFilter(f"invalid_field: field must be one of {', '.join(FIELDS)}")
    return field


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
        "field": row.field,
        "previous_value": row.previous_value,
        "new_value": row.new_value,
        "previous_label": row.previous_label,
        "new_label": row.new_label,
        "reason": row.reason,
        "effective_date": row.effective_date,
        "changed_by": row.changed_by,
        "created_at": row.created_at,
    }


async def list_changes_feed(
    session: AsyncSession,
    *,
    secret: str,
    employee_id: str | None,
    department_id: int | None,
    field: str | None,
    since: str | None,
    until: str | None,
    changed_by: str | None,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    previous = aliased(Department)
    new = aliased(Department)
    stmt = (
        select(
            Change.id,
            Change.employee_id,
            Employee.employee_number,
            Employee.first_name,
            Employee.last_name,
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            Change.field,
            Change.previous_value,
            Change.new_value,
            previous.name.label("previous_label"),
            new.name.label("new_label"),
            Change.reason,
            Change.effective_date,
            Change.changed_by,
            Change.created_at,
        )
        .join(Employee, Employee.id == Change.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .outerjoin(
            previous,
            and_(
                Change.field == _DEPARTMENT_FIELD,
                previous.id == cast(Change.previous_value, Integer),
            ),
        )
        .outerjoin(
            new,
            and_(
                Change.field == _DEPARTMENT_FIELD,
                new.id == cast(Change.new_value, Integer),
            ),
        )
    )
    if employee_id:
        stmt = stmt.where(Change.employee_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if field:
        stmt = stmt.where(Change.field == field)
    if since is not None:
        stmt = stmt.where(Change.effective_date >= since)
    if until is not None:
        stmt = stmt.where(Change.effective_date <= until)
    if changed_by:
        stmt = stmt.where(Change.changed_by == changed_by)
    if cursor:
        created_at, row_id = _decode(secret, cursor)
        stmt = stmt.where(
            or_(
                Change.created_at < created_at,
                and_(Change.created_at == created_at, Change.id < row_id),
            )
        )
    stmt = stmt.order_by(Change.created_at.desc(), Change.id.desc()).limit(limit + 1)
    fetched = (await session.execute(stmt)).all()
    rows = fetched[:limit]
    next_cursor = None
    if len(fetched) > limit:
        last = rows[-1]
        next_cursor = sign_cursor(
            secret, {"kind": _KIND, "created_at": last.created_at, "id": int(last.id)}
        )
    return {"items": [_item(row) for row in rows], "next_cursor": next_cursor}
