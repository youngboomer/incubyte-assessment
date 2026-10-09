from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_hr
from app.directory import InvalidCursor, export_employees_csv, get_employee, list_employees

router = APIRouter(prefix="/employees", tags=["employees"])

_Sort = Literal[
    "name",
    "employee_number",
    "department",
    "country",
    "title",
    "base_salary",
    "salary_usd",
    "hire_date",
]
_Direction = Literal["asc", "desc"]


@router.get("")
async def read_employees(
    request: Request,
    q: str | None = None,
    department_id: int | None = None,
    country: str | None = None,
    currency: str | None = None,
    status: str | None = None,
    sort: _Sort = "name",
    direction: _Direction = "asc",
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        return await list_employees(
            session,
            secret=request.app.state.settings.app_secret,
            q=q,
            department_id=department_id,
            country=country,
            currency=currency,
            status=status,
            sort=sort,
            direction=direction,
            limit=limit,
            cursor=cursor,
        )
    except InvalidCursor as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/export.csv")
async def export_employees(
    q: str | None = None,
    department_id: int | None = None,
    country: str | None = None,
    currency: str | None = None,
    status: str | None = None,
    sort: _Sort = "name",
    direction: _Direction = "asc",
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> Response:
    body = await export_employees_csv(
        session,
        q=q,
        department_id=department_id,
        country=country,
        currency=currency,
        status=status,
        sort=sort,
        direction=direction,
    )
    return Response(content=body, media_type="text/csv")


@router.get("/{employee_id}")
async def read_employee(
    employee_id: str,
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    employee = await get_employee(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
