from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_feed import InvalidFilter, list_audit_feed, parse_iso_date
from app.db import get_session
from app.deps import require_hr
from app.directory import InvalidCursor

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def read_audit_feed(
    request: Request,
    employee_id: str | None = None,
    department_id: int | None = None,
    since: str | None = None,
    until: str | None = None,
    changed_by: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        start = parse_iso_date("since", since)
        end = parse_iso_date("until", until)
        if start is not None and end is not None and start > end:
            raise InvalidFilter("invalid_date_range: since is after until")
        return await list_audit_feed(
            session,
            secret=request.app.state.settings.app_secret,
            employee_id=employee_id,
            department_id=department_id,
            since=start,
            until=end,
            changed_by=changed_by,
            limit=limit,
            cursor=cursor,
        )
    except (InvalidFilter, InvalidCursor) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
