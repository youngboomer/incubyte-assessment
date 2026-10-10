import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompensationAuditLog, Country, Currency, Department, Employee
from app.money import decimal_to_scaled, scaled_to_decimal

FX_SCALE = 6
USD_SCALE = 2
LEVELS = frozenset({"IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"})
STATUSES = frozenset({"active", "terminated"})
_NUMBER_ATTEMPTS = 10
_NUMBER_TAKEN = "Employee number already exists"

# RETURNING id is set only when the version predicate matches. The FTS trigger
# also writes on this update, so changes() is not a reliable row count.
_COMPENSATION_UPDATE = text(
    """
    UPDATE employees
    SET base_salary_scaled = :base,
        variable_pay_scaled = :variable,
        salary_usd_scaled = :usd,
        comp_effective_date = :effective_date,
        version_id = version_id + 1,
        updated_at = :now
    WHERE id = :id AND version_id = :expected
    RETURNING id
    """
)
_CURRENCY_UPDATE = text(
    """
    UPDATE currencies
    SET units_per_usd_scaled = :units_per_usd_scaled,
        updated_at = :updated_at
    WHERE code = :code
    RETURNING code
    """
)
_NEXT_EMPLOYEE_NUMBER = text(
    """
    SELECT MAX(CAST(SUBSTR(employee_number, 5) AS INTEGER))
    FROM employees
    WHERE employee_number LIKE 'EMP-%'
    """
)


@dataclass(frozen=True)
class NewEmployee:
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
    hire_date: str
    comp_effective_date: str


@dataclass(frozen=True)
class CompensationChange:
    base_salary_scaled: str
    variable_pay_scaled: str
    reason: str
    effective_date: str
    version_id: int


@dataclass(frozen=True)
class NotFound:
    detail: str


@dataclass(frozen=True)
class Conflict:
    detail: str


@dataclass(frozen=True)
class Unprocessable:
    detail: str


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def compute_salary_usd_scaled(
    base_salary_scaled: str,
    variable_pay_scaled: str,
    minor_scale: int,
    units_per_usd_scaled: str,
) -> str:
    local = scaled_to_decimal(base_salary_scaled, minor_scale) + scaled_to_decimal(
        variable_pay_scaled, minor_scale
    )
    usd = local / scaled_to_decimal(units_per_usd_scaled, FX_SCALE)
    return decimal_to_scaled(usd, USD_SCALE)


def _employee_statement(employee_id: str) -> Any:
    return (
        select(
            Employee.id,
            Employee.employee_number,
            Employee.first_name,
            Employee.last_name,
            Employee.email,
            Employee.job_title,
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            Country.code.label("country_code"),
            Country.name.label("country_name"),
            Employee.currency_code,
            Employee.level,
            Employee.base_salary_scaled,
            Employee.variable_pay_scaled,
            Currency.minor_scale.label("salary_scale"),
            Employee.salary_usd_scaled,
            Employee.status,
            Employee.hire_date,
            Employee.comp_effective_date,
            Employee.version_id,
            Currency.units_per_usd_scaled,
        )
        .join(Department, Department.id == Employee.department_id)
        .join(Country, Country.code == Employee.country_code)
        .join(Currency, Currency.code == Employee.currency_code)
        .where(Employee.id == employee_id)
    )


def _employee_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "employee_number": row["employee_number"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "job_title": row["job_title"],
        "department": {"id": int(row["department_id"]), "name": row["department_name"]},
        "country": {"code": row["country_code"], "name": row["country_name"]},
        "currency_code": row["currency_code"],
        "level": row["level"],
        "base_salary_scaled": row["base_salary_scaled"],
        "variable_pay_scaled": row["variable_pay_scaled"],
        "salary_scale": int(row["salary_scale"]),
        "salary_usd_scaled": row["salary_usd_scaled"],
        "salary_usd_scale": USD_SCALE,
        "status": row["status"],
        "hire_date": row["hire_date"],
        "comp_effective_date": row["comp_effective_date"],
        "version_id": int(row["version_id"]),
    }


def _audit_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "previous_base_salary_scaled": row["previous_base_salary_scaled"],
        "new_base_salary_scaled": row["new_base_salary_scaled"],
        "previous_variable_pay_scaled": row["previous_variable_pay_scaled"],
        "new_variable_pay_scaled": row["new_variable_pay_scaled"],
        "salary_scale": int(row["salary_scale"]),
        "currency_code": row["currency_code"],
        "fx_units_per_usd_scaled": row["fx_units_per_usd_scaled"],
        "fx_scale": FX_SCALE,
        "previous_salary_usd_scaled": row["previous_salary_usd_scaled"],
        "new_salary_usd_scaled": row["new_salary_usd_scaled"],
        "salary_usd_scale": USD_SCALE,
        "reason": row["reason"],
        "effective_date": row["effective_date"],
        "changed_by": row["changed_by"],
        "created_at": row["created_at"],
    }


def _currency_payload(
    code: str, name: str, minor_scale: int, units_per_usd_scaled: str
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "minor_scale": int(minor_scale),
        "units_per_usd_scaled": units_per_usd_scaled,
        "units_per_usd_scale": FX_SCALE,
    }


async def _fetch_employee(session: AsyncSession, employee_id: str) -> RowMapping | None:
    result = await session.execute(_employee_statement(employee_id))
    return result.mappings().one_or_none()


async def _next_employee_number(session: AsyncSession) -> str:
    current = (await session.execute(_NEXT_EMPLOYEE_NUMBER)).scalar_one()
    # At least five digits: EMP-00001, and EMP-100000 once the sequence passes 99999.
    next_number = 1 if current is None else int(current) + 1
    return f"EMP-{next_number:05d}"


async def _insert_audit(session: AsyncSession, values: dict[str, object]) -> None:
    await session.execute(insert(CompensationAuditLog).values(**values))


def _conflict_from_integrity(exc: IntegrityError) -> Conflict:
    message = str(exc.orig).lower()
    if "unique" not in message:
        raise exc
    if "employee_number" in message:
        return Conflict(_NUMBER_TAKEN)
    return Conflict("Email already exists")


async def create_employee(
    session: AsyncSession, new_employee: NewEmployee
) -> dict[str, Any] | Conflict | Unprocessable:
    if new_employee.level not in LEVELS:
        return Unprocessable("Invalid level")
    if new_employee.status not in STATUSES:
        return Unprocessable("Invalid status")

    department_id = (
        await session.execute(
            select(Department.id).where(Department.id == new_employee.department_id)
        )
    ).scalar_one_or_none()
    if department_id is None:
        return Unprocessable("Unknown department")

    currency_code = (
        await session.execute(
            select(Country.currency_code).where(Country.code == new_employee.country_code)
        )
    ).scalar_one_or_none()
    if currency_code is None:
        return Unprocessable("Unknown country")

    currency = (
        await session.execute(
            select(Currency.minor_scale, Currency.units_per_usd_scaled).where(
                Currency.code == currency_code
            )
        )
    ).one_or_none()
    if currency is None:
        return Unprocessable("Unknown currency")

    duplicate = (
        await session.execute(select(Employee.id).where(Employee.email == new_employee.email))
    ).first()
    if duplicate is not None:
        return Conflict("Email already exists")

    try:
        usd = compute_salary_usd_scaled(
            new_employee.base_salary_scaled,
            new_employee.variable_pay_scaled,
            int(currency.minor_scale),
            str(currency.units_per_usd_scaled),
        )
    except (ValueError, ArithmeticError):
        return Unprocessable("Invalid salary")

    now = utc_timestamp()
    employee_id = str(uuid.uuid4())
    for attempt in range(_NUMBER_ATTEMPTS):
        employee_number = await _next_employee_number(session)
        try:
            await session.execute(
                insert(Employee).values(
                    id=employee_id,
                    employee_number=employee_number,
                    first_name=new_employee.first_name,
                    last_name=new_employee.last_name,
                    email=new_employee.email,
                    job_title=new_employee.job_title,
                    department_id=new_employee.department_id,
                    country_code=new_employee.country_code,
                    currency_code=currency_code,
                    level=new_employee.level,
                    base_salary_scaled=new_employee.base_salary_scaled,
                    variable_pay_scaled=new_employee.variable_pay_scaled,
                    salary_usd_scaled=usd,
                    status=new_employee.status,
                    hire_date=new_employee.hire_date,
                    comp_effective_date=new_employee.comp_effective_date,
                    version_id=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            created = await _fetch_employee(session, employee_id)
            if created is None:
                await session.rollback()
                return Unprocessable("Unknown department")
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            conflict = _conflict_from_integrity(exc)
            if conflict.detail == _NUMBER_TAKEN and attempt + 1 < _NUMBER_ATTEMPTS:
                continue
            return conflict
        return _employee_payload(created)
    raise AssertionError("unreachable: the last attempt returns")


async def update_compensation(
    session: AsyncSession,
    employee_id: str,
    change: CompensationChange,
    changed_by: str,
) -> dict[str, Any] | NotFound | Conflict | Unprocessable:
    if not change.reason:
        return Unprocessable("Reason is required")

    current = await _fetch_employee(session, employee_id)
    if current is None:
        return NotFound("Employee not found")

    try:
        usd = compute_salary_usd_scaled(
            change.base_salary_scaled,
            change.variable_pay_scaled,
            int(current["salary_scale"]),
            str(current["units_per_usd_scaled"]),
        )
    except (ValueError, ArithmeticError):
        return Unprocessable("Invalid salary")

    now = utc_timestamp()
    try:
        matched = (
            await session.execute(
                _COMPENSATION_UPDATE,
                {
                    "base": change.base_salary_scaled,
                    "variable": change.variable_pay_scaled,
                    "usd": usd,
                    "effective_date": change.effective_date,
                    "now": now,
                    "id": employee_id,
                    "expected": change.version_id,
                },
            )
        ).scalar_one_or_none()
        if matched is None:
            await session.rollback()
            still = await _fetch_employee(session, employee_id)
            if still is None:
                return NotFound("Employee not found")
            return Conflict("Record was modified. Reload and try again.")

        await _insert_audit(
            session,
            {
                "employee_id": employee_id,
                "previous_base_salary_scaled": current["base_salary_scaled"],
                "new_base_salary_scaled": change.base_salary_scaled,
                "previous_variable_pay_scaled": current["variable_pay_scaled"],
                "new_variable_pay_scaled": change.variable_pay_scaled,
                "currency_code": current["currency_code"],
                "fx_units_per_usd_scaled": current["units_per_usd_scaled"],
                "previous_salary_usd_scaled": current["salary_usd_scaled"],
                "new_salary_usd_scaled": usd,
                "reason": change.reason,
                "effective_date": change.effective_date,
                "changed_by": changed_by,
                "created_at": now,
            },
        )
        updated = await _fetch_employee(session, employee_id)
        if updated is None:
            await session.rollback()
            return NotFound("Employee not found")
        # Salary update and audit insert commit together.
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return _employee_payload(updated)


async def list_audit(
    session: AsyncSession, employee_id: str
) -> dict[str, list[dict[str, Any]]] | NotFound:
    exists = (
        await session.execute(select(Employee.id).where(Employee.id == employee_id))
    ).first()
    if exists is None:
        return NotFound("Employee not found")

    rows = (
        await session.execute(
            select(
                CompensationAuditLog.id,
                CompensationAuditLog.previous_base_salary_scaled,
                CompensationAuditLog.new_base_salary_scaled,
                CompensationAuditLog.previous_variable_pay_scaled,
                CompensationAuditLog.new_variable_pay_scaled,
                Currency.minor_scale.label("salary_scale"),
                CompensationAuditLog.currency_code,
                CompensationAuditLog.fx_units_per_usd_scaled,
                CompensationAuditLog.previous_salary_usd_scaled,
                CompensationAuditLog.new_salary_usd_scaled,
                CompensationAuditLog.reason,
                CompensationAuditLog.effective_date,
                CompensationAuditLog.changed_by,
                CompensationAuditLog.created_at,
            )
            .join(Currency, Currency.code == CompensationAuditLog.currency_code)
            .where(CompensationAuditLog.employee_id == employee_id)
            .order_by(CompensationAuditLog.created_at.desc(), CompensationAuditLog.id.desc())
        )
    ).mappings().all()
    return {"items": [_audit_payload(row) for row in rows]}


async def list_currencies(session: AsyncSession) -> list[dict[str, Any]]:
    rows = (await session.execute(select(Currency).order_by(Currency.code.asc()))).scalars().all()
    return [
        _currency_payload(row.code, row.name, row.minor_scale, row.units_per_usd_scaled)
        for row in rows
    ]


async def update_exchange_rate(
    session: AsyncSession, code: str, units_per_usd_scaled: str
) -> dict[str, Any] | NotFound | Unprocessable:
    try:
        rate = scaled_to_decimal(units_per_usd_scaled, FX_SCALE)
    except ValueError:
        return Unprocessable("Invalid exchange rate")
    if rate == 0:
        return Unprocessable("Invalid exchange rate")

    currency = (
        await session.execute(select(Currency).where(Currency.code == code))
    ).scalar_one_or_none()
    if currency is None:
        return NotFound("Currency not found")

    employees = (
        (
            await session.execute(
                select(
                    Employee.id,
                    Employee.base_salary_scaled,
                    Employee.variable_pay_scaled,
                    Currency.minor_scale,
                )
                .join(Currency, Currency.code == Employee.currency_code)
                .where(Employee.currency_code == code)
            )
        )
        .mappings()
        .all()
    )
    recomputed: list[dict[str, str]] = []
    for employee in employees:
        try:
            usd = compute_salary_usd_scaled(
                str(employee["base_salary_scaled"]),
                str(employee["variable_pay_scaled"]),
                int(employee["minor_scale"]),
                units_per_usd_scaled,
            )
        except (ValueError, ArithmeticError):
            return Unprocessable("Invalid exchange rate")
        recomputed.append({"id": str(employee["id"]), "usd": usd})

    payload = _currency_payload(
        currency.code, currency.name, currency.minor_scale, units_per_usd_scaled
    )
    now = utc_timestamp()
    try:
        matched = (
            await session.execute(
                _CURRENCY_UPDATE,
                {
                    "units_per_usd_scaled": units_per_usd_scaled,
                    "updated_at": now,
                    "code": code,
                },
            )
        ).scalar_one_or_none()
        if matched is None:
            await session.rollback()
            return NotFound("Currency not found")
        if recomputed:
            await session.execute(
                text("UPDATE employees SET salary_usd_scaled = :usd WHERE id = :id"),
                recomputed,
            )
        # Rate update and USD recompute commit together. Audit rows are not updated.
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return payload
