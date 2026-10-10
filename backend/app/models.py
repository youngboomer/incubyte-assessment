from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, literal_column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    minor_scale: Mapped[int] = mapped_column(Integer, nullable=False)
    units_per_usd_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        Text, ForeignKey("currencies.code"), nullable=False
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'terminated')",
            name="ck_employees_status",
        ),
        Index("idx_emp_status_dept", "status", "department_id"),
        Index("idx_emp_status_country", "status", "country_code"),
        Index("idx_emp_status_currency", "status", "currency_code"),
        Index(
            "idx_emp_salary_usd",
            literal_column("CAST(salary_usd_scaled AS INTEGER)"),
            "id",
        ),
        Index(
            "idx_emp_base_salary",
            literal_column("CAST(base_salary_scaled AS INTEGER)"),
            "id",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    employee_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    job_title: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=False
    )
    country_code: Mapped[str] = mapped_column(
        Text, ForeignKey("countries.code"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(
        Text, ForeignKey("currencies.code"), nullable=False
    )
    level: Mapped[str] = mapped_column(Text, nullable=False)
    base_salary_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    variable_pay_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    salary_usd_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    hire_date: Mapped[str] = mapped_column(Text, nullable=False)
    comp_effective_date: Mapped[str] = mapped_column(Text, nullable=False)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class CompensationAuditLog(Base):
    __tablename__ = "compensation_audit_logs"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        Text, ForeignKey("employees.id"), nullable=False
    )
    previous_base_salary_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    new_base_salary_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    previous_variable_pay_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    new_variable_pay_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    currency_code: Mapped[str] = mapped_column(Text, nullable=False)
    fx_units_per_usd_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    previous_salary_usd_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    new_salary_usd_scaled: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class EmployeeChangeLog(Base):
    __tablename__ = "employee_change_logs"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(
        Text, ForeignKey("employees.id"), nullable=False
    )
    field: Mapped[str] = mapped_column(Text, nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
