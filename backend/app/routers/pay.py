import re
from datetime import date

from fastapi import Depends, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.routing import Match
from starlette.types import Scope

from app.compensation import (
    LEVELS,
    STATUSES,
    CompensationChange,
    Conflict,
    NewEmployee,
    NotFound,
    Unprocessable,
    create_employee,
    list_audit,
    update_compensation,
)
from app.db import get_session
from app.deps import require_hr
from app.money import scaled_to_decimal
from app.routers.employees import router

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class _PostEmployeeRoute(APIRoute):
    """A wrong method is not a partial match.

    GET /employees must stay 404 until a GET route exists. Starlette would
    otherwise answer 405 because POST /employees matches the path.
    """

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        match, child_scope = super().matches(scope)
        if match == Match.PARTIAL:
            return Match.NONE, {}
        return match, child_scope


def _stripped(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty")
    return value


def _scaled_amount(value: str) -> str:
    if scaled_to_decimal(value, 0) < 0:
        raise ValueError("must not be negative")
    return value


def _raise_for_result(result: object) -> None:
    if isinstance(result, NotFound):
        raise HTTPException(status_code=404, detail=result.detail)
    if isinstance(result, Conflict):
        raise HTTPException(status_code=409, detail=result.detail)
    if isinstance(result, Unprocessable):
        raise HTTPException(status_code=422, detail=result.detail)


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    email: str
    job_title: str
    department_id: int
    country_code: str
    level: str
    base_salary_scaled: str
    variable_pay_scaled: str
    status: str
    hire_date: date
    comp_effective_date: date

    @field_validator("first_name", "last_name", "email", "job_title", "country_code")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        return _stripped(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        if _EMAIL_RE.fullmatch(value) is None:
            raise ValueError("must be an email address")
        return value

    @field_validator("base_salary_scaled", "variable_pay_scaled")
    @classmethod
    def _salary(cls, value: str) -> str:
        return _scaled_amount(value)

    @field_validator("level")
    @classmethod
    def _level(cls, value: str) -> str:
        if value not in LEVELS:
            raise ValueError("invalid level")
        return value

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in STATUSES:
            raise ValueError("invalid status")
        return value


class CompensationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_salary_scaled: str
    variable_pay_scaled: str
    reason: str
    effective_date: date
    version_id: int

    @field_validator("base_salary_scaled", "variable_pay_scaled")
    @classmethod
    def _salary(cls, value: str) -> str:
        return _scaled_amount(value)

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        return _stripped(value)


async def post_employee(
    body: EmployeeCreate,
    session: AsyncSession = Depends(get_session),
    _actor: str = Depends(require_hr),
) -> dict[str, object]:
    result = await create_employee(
        session,
        NewEmployee(
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            job_title=body.job_title,
            department_id=body.department_id,
            country_code=body.country_code,
            level=body.level,
            base_salary_scaled=body.base_salary_scaled,
            variable_pay_scaled=body.variable_pay_scaled,
            status=body.status,
            hire_date=body.hire_date.isoformat(),
            comp_effective_date=body.comp_effective_date.isoformat(),
        ),
    )
    _raise_for_result(result)
    return result


router.add_api_route("", post_employee, methods=["POST"], route_class_override=_PostEmployeeRoute)


@router.patch("/{employee_id}/compensation")
async def patch_compensation(
    employee_id: str,
    body: CompensationPatch,
    session: AsyncSession = Depends(get_session),
    changed_by: str = Depends(require_hr),
) -> dict[str, object]:
    result = await update_compensation(
        session,
        employee_id,
        CompensationChange(
            base_salary_scaled=body.base_salary_scaled,
            variable_pay_scaled=body.variable_pay_scaled,
            reason=body.reason,
            effective_date=body.effective_date.isoformat(),
            version_id=body.version_id,
        ),
        changed_by,
    )
    _raise_for_result(result)
    return result


@router.get("/{employee_id}/audit")
async def get_audit(
    employee_id: str,
    session: AsyncSession = Depends(get_session),
    _actor: str = Depends(require_hr),
) -> dict[str, object]:
    result = await list_audit(session, employee_id)
    _raise_for_result(result)
    return result
