from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.deps import issue_token
from app.main import create_app
from app.settings import Settings

_NEW_EMPLOYEE = {
    "first_name": "Ada",
    "last_name": "Okoye",
    "email": "ada.okoye@acme.test",
    "job_title": "Software Engineer",
    "department_id": 1,
    "country_code": "US",
    "level": "IC3",
    "base_salary_scaled": "15500000",
    "variable_pay_scaled": "0",
    "status": "active",
    "hire_date": "2026-01-15",
    "comp_effective_date": "2026-01-15",
}
_AUDIT_FIELDS = {"reason": "why", "effective_date": "2026-02-01", "version_id": 1}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    url = "sqlite+aiosqlite:///" + (tmp_path / "comppulse.db").resolve().as_posix()
    settings = Settings(database_url=url, seed_count=0, login_max_attempts=10_000)
    app = create_app(settings)
    with TestClient(app) as test_client:
        token = issue_token(settings.app_secret, settings.hr_email)
        test_client.headers["authorization"] = f"Bearer {token}"
        yield test_client


def _schema_rejected(response: Response) -> bool:
    return response.status_code == 422 and isinstance(response.json()["detail"], list)


def _scaled(length: int) -> str:
    return "0" * (length - 1) + "1"


def _email(length: int) -> str:
    return "a" * (length - len("@acme.test")) + "@acme.test"


def _login(client: TestClient, email: str, password: str) -> Response:
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_limits(client: TestClient) -> None:
    assert not _schema_rejected(_login(client, _email(254), "p" * 256))
    assert _schema_rejected(_login(client, _email(255), "p"))
    assert _schema_rejected(_login(client, "a@acme.test", "p" * 257))


@pytest.mark.parametrize(
    "field,limit,make",
    [
        ("first_name", 100, lambda n: "a" * n),
        ("last_name", 100, lambda n: "a" * n),
        ("job_title", 120, lambda n: "a" * n),
        ("email", 254, _email),
        ("base_salary_scaled", 20, _scaled),
        ("variable_pay_scaled", 20, _scaled),
        ("country_code", 8, lambda n: "U" * n),
    ],
)
def test_create_employee_limits(client: TestClient, field: str, limit: int, make) -> None:
    at_limit = client.post("/employees", json={**_NEW_EMPLOYEE, field: make(limit)})
    assert not _schema_rejected(at_limit)
    over = client.post("/employees", json={**_NEW_EMPLOYEE, field: make(limit + 1)})
    assert _schema_rejected(over)


@pytest.mark.parametrize(
    "field,limit,make",
    [
        ("first_name", 100, lambda n: "a" * n),
        ("last_name", 100, lambda n: "a" * n),
        ("job_title", 120, lambda n: "a" * n),
        ("email", 254, _email),
        ("reason", 500, lambda n: "r" * n),
    ],
)
def test_patch_employee_limits(client: TestClient, field: str, limit: int, make) -> None:
    body = {"first_name": "Ada", **_AUDIT_FIELDS, field: make(limit)}
    assert not _schema_rejected(client.patch("/employees/nope", json=body))
    body[field] = make(limit + 1)
    assert _schema_rejected(client.patch("/employees/nope", json=body))


@pytest.mark.parametrize(
    "field,limit,make",
    [
        ("base_salary_scaled", 20, _scaled),
        ("variable_pay_scaled", 20, _scaled),
        ("reason", 500, lambda n: "r" * n),
    ],
)
def test_patch_compensation_limits(client: TestClient, field: str, limit: int, make) -> None:
    body = {"base_salary_scaled": "1", "variable_pay_scaled": "0", **_AUDIT_FIELDS}
    body[field] = make(limit)
    assert not _schema_rejected(client.patch("/employees/nope/compensation", json=body))
    body[field] = make(limit + 1)
    assert _schema_rejected(client.patch("/employees/nope/compensation", json=body))


def test_status_reason_limit(client: TestClient) -> None:
    body = {"status": "terminated", **_AUDIT_FIELDS, "reason": "r" * 500}
    assert not _schema_rejected(client.post("/employees/nope/status", json=body))
    body["reason"] = "r" * 501
    assert _schema_rejected(client.post("/employees/nope/status", json=body))


def test_fx_rate_limit(client: TestClient) -> None:
    ok = client.patch("/fx/USD", json={"units_per_usd_scaled": _scaled(20)})
    assert not _schema_rejected(ok)
    over = client.patch("/fx/USD", json={"units_per_usd_scaled": _scaled(21)})
    assert _schema_rejected(over)


@pytest.mark.parametrize(
    "path,param,limit",
    [
        ("/employees", "q", 200),
        ("/employees", "country", 8),
        ("/employees", "currency", 8),
        ("/employees", "salary_usd_min", 20),
        ("/employees", "salary_usd_max", 20),
        ("/employees", "cursor", 512),
        ("/employees/export.csv", "q", 200),
        ("/audit", "changed_by", 254),
        ("/audit", "employee_id", 64),
        ("/audit", "since", 40),
        ("/audit", "until", 40),
        ("/audit", "cursor", 512),
    ],
)
def test_query_param_limits(client: TestClient, path: str, param: str, limit: int) -> None:
    at_limit = client.get(path, params={param: "1" * limit})
    assert not _schema_rejected(at_limit)
    assert _schema_rejected(client.get(path, params={param: "1" * (limit + 1)}))
