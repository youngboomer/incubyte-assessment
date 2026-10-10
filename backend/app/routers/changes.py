from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_feed import InvalidFilter, parse_iso_date
from app.changes_feed import list_changes_feed, validate_field
from app.db import get_session
from app.deps import require_hr
from app.directory import InvalidCursor

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("")
async def read_changes_feed(
    request: Request,
    employee_id: str | None = Query(default=None, max_length=64),
    department_id: int | None = None,
    field: str | None = Query(default=None, max_length=32),
    since: str | None = Query(default=None, max_length=40),
    until: str | None = Query(default=None, max_length=40),
    changed_by: str | None = Query(default=None, max_length=254),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=512),
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        validate_field(field)
        start = parse_iso_date("since", since)
        end = parse_iso_date("until", until)
        if start is not None and end is not None and start > end:
            raise InvalidFilter("invalid_date_range: since is after until")
        return await list_changes_feed(
            session,
            secret=request.app.state.settings.app_secret,
            employee_id=employee_id,
            department_id=department_id,
            field=field,
            since=start,
            until=end,
            changed_by=changed_by,
            limit=limit,
            cursor=cursor,
        )
    except (InvalidFilter, InvalidCursor) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
