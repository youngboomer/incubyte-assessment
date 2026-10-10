from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_hr
from app.directory import (
    InvalidCursor,
    InvalidFilter,
    export_employees_csv,
    get_employee,
    list_employees,
    parse_salary_usd_bound,
)

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
_Level = Literal["IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"]
_Status = Literal["active", "terminated"]


def _salary_range(
    salary_usd_min: str | None, salary_usd_max: str | None
) -> tuple[int | None, int | None]:
    try:
        low = parse_salary_usd_bound(salary_usd_min)
        high = parse_salary_usd_bound(salary_usd_max)
    except InvalidFilter as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if low is not None and high is not None and low > high:
        raise HTTPException(
            status_code=422, detail="invalid_salary_range: salary_usd_min exceeds salary_usd_max"
        )
    return low, high


@router.get("")
async def read_employees(
    request: Request,
    q: str | None = None,
    department_id: int | None = None,
    country: str | None = None,
    currency: str | None = None,
    status: _Status | None = None,
    level: _Level | None = None,
    salary_usd_min: str | None = None,
    salary_usd_max: str | None = None,
    sort: _Sort = "name",
    direction: _Direction = "asc",
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    low, high = _salary_range(salary_usd_min, salary_usd_max)
    try:
        return await list_employees(
            session,
            secret=request.app.state.settings.app_secret,
            q=q,
            department_id=department_id,
            country=country,
            currency=currency,
            status=status,
            level=level,
            salary_usd_min=low,
            salary_usd_max=high,
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
    status: _Status | None = None,
    level: _Level | None = None,
    salary_usd_min: str | None = None,
    salary_usd_max: str | None = None,
    sort: _Sort = "name",
    direction: _Direction = "asc",
    _: str = Depends(require_hr),
    session: AsyncSession = Depends(get_session),
) -> Response:
    low, high = _salary_range(salary_usd_min, salary_usd_max)
    body = await export_employees_csv(
        session,
        q=q,
        department_id=department_id,
        country=country,
        currency=currency,
        status=status,
        level=level,
        salary_usd_min=low,
        salary_usd_max=high,
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
