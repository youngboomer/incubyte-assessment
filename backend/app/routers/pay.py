import re
from datetime import date
from typing import Self

from fastapi import Depends, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.routing import Match
from starlette.types import Scope

from app.compensation import (
    LEVELS,
    STATUSES,
    CompensationChange,
    Conflict,
    EmployeeEdit,
    NewEmployee,
    NotFound,
    StatusChange,
    Unprocessable,
    change_status,
    create_employee,
    list_audit,
    list_changes,
    update_compensation,
    update_employee,
)
from app.db import get_session
from app.deps import require_hr
from app.money import scaled_to_decimal
from app.routers.employees import router

_EDITABLE_FIELDS = ("first_name", "last_name", "email", "job_title", "department_id", "level")
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

    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(max_length=254)
    job_title: str = Field(max_length=120)
    department_id: int
    country_code: str = Field(max_length=8)
    level: str = Field(max_length=32)
    base_salary_scaled: str = Field(max_length=20)
    variable_pay_scaled: str = Field(max_length=20)
    status: str = Field(max_length=32)
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

    base_salary_scaled: str = Field(max_length=20)
    variable_pay_scaled: str = Field(max_length=20)
    reason: str = Field(max_length=500)
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


class EmployeePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=254)
    job_title: str | None = Field(default=None, max_length=120)
    department_id: int | None = None
    level: str | None = Field(default=None, max_length=32)
    reason: str = Field(max_length=500)
    effective_date: date
    version_id: int

    @model_validator(mode="after")
    def _has_a_field(self) -> Self:
        provided = self.model_fields_set.intersection(_EDITABLE_FIELDS)
        if not provided:
            raise ValueError("at least one field to change is required")
        if any(getattr(self, name) is None for name in provided):
            raise ValueError("fields must not be null")
        return self

    @field_validator("first_name", "last_name", "email", "job_title", "reason")
    @classmethod
    def _non_empty(cls, value: str | None) -> str | None:
        return None if value is None else _stripped(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if value is not None and _EMAIL_RE.fullmatch(value) is None:
            raise ValueError("must be an email address")
        return value

    @field_validator("level")
    @classmethod
    def _level(cls, value: str | None) -> str | None:
        if value is not None and value not in LEVELS:
            raise ValueError("invalid level")
        return value

    def changes(self) -> dict[str, str | int]:
        return {
            name: getattr(self, name)
            for name in _EDITABLE_FIELDS
            if name in self.model_fields_set
        }


class StatusPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(max_length=32)
    reason: str = Field(max_length=500)
    effective_date: date
    version_id: int

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        return _stripped(value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in STATUSES:
            raise ValueError("invalid status")
        return value


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


@router.patch("/{employee_id}")
async def patch_employee(
    employee_id: str,
    body: EmployeePatch,
    session: AsyncSession = Depends(get_session),
    changed_by: str = Depends(require_hr),
) -> dict[str, object]:
    result = await update_employee(
        session,
        employee_id,
        EmployeeEdit(
            fields=body.changes(),
            reason=body.reason,
            effective_date=body.effective_date.isoformat(),
            version_id=body.version_id,
        ),
        changed_by,
    )
    _raise_for_result(result)
    return result


@router.post("/{employee_id}/status")
async def post_status(
    employee_id: str,
    body: StatusPost,
    session: AsyncSession = Depends(get_session),
    changed_by: str = Depends(require_hr),
) -> dict[str, object]:
    result = await change_status(
        session,
        employee_id,
        StatusChange(
            status=body.status,
            reason=body.reason,
            effective_date=body.effective_date.isoformat(),
            version_id=body.version_id,
        ),
        changed_by,
    )
    _raise_for_result(result)
    return result


@router.get("/{employee_id}/changes")
async def get_changes(
    employee_id: str,
    session: AsyncSession = Depends(get_session),
    _actor: str = Depends(require_hr),
) -> dict[str, object]:
    result = await list_changes(session, employee_id)
    _raise_for_result(result)
    return result
