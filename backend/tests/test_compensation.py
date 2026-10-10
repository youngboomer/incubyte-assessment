import sqlite3
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.deps import issue_token
from app.main import create_app
from app.money import decimal_to_scaled, scaled_to_decimal
from app.settings import Settings

_EMPLOYEE_SQL = """
INSERT INTO employees (
  id, employee_number, first_name, last_name, email, job_title,
  department_id, country_code, currency_code, level,
  base_salary_scaled, variable_pay_scaled, salary_usd_scaled,
  status, hire_date, comp_effective_date, version_id, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def _expected_usd(base: str, variable: str, scale: int, rate: str) -> str:
    local = scaled_to_decimal(base, scale) + scaled_to_decimal(variable, scale)
    usd = local / scaled_to_decimal(rate, 6)
    return decimal_to_scaled(usd, 2)


def _body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return payload


def _comp(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "base_salary_scaled": "16000000",
        "variable_pay_scaled": "0",
        "reason": "Annual review",
        "effective_date": "2026-04-01",
        "version_id": 1,
    }
    payload.update(overrides)
    return payload


def _seed(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        connection.executemany(
            "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("USD", "US Dollar", 2, "1000000", "2026-01-01T00:00:00Z"),
                ("GBP", "British Pound", 2, "780000", "2026-01-01T00:00:00Z"),
                ("JPY", "Japanese Yen", 0, "149000000", "2026-01-01T00:00:00Z"),
                ("INR", "Indian Rupee", 2, "83500000", "2026-01-01T00:00:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO countries (code, name, currency_code) VALUES (?, ?, ?)",
            [
                ("US", "United States", "USD"),
                ("GB", "United Kingdom", "GBP"),
                ("JP", "Japan", "JPY"),
                ("IN", "India", "INR"),
            ],
        )
        connection.executemany(
            "INSERT INTO departments (id, name) VALUES (?, ?)",
            [(1, "Engineering"), (2, "Sales")],
        )
        connection.commit()
    finally:
        connection.close()


def _insert_employee(
    db_path: Path,
    employee_id: str,
    employee_number: str,
    email: str,
    *,
    currency_code: str = "USD",
    country_code: str = "US",
    base_salary_scaled: str = "10000",
    variable_pay_scaled: str = "0",
    salary_usd_scaled: str = "10000",
    status: str = "active",
    version_id: int = 1,
    updated_at: str = "2026-01-01T00:00:00Z",
) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute(
            _EMPLOYEE_SQL,
            (
                employee_id,
                employee_number,
                "Ada",
                "Okoye",
                email,
                "Software Engineer",
                1,
                country_code,
                currency_code,
                "IC3",
                base_salary_scaled,
                variable_pay_scaled,
                salary_usd_scaled,
                status,
                "2026-01-15",
                "2026-01-15",
                version_id,
                "2026-01-01T00:00:00Z",
                updated_at,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _query(db_path: Path, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        return list(connection.execute(sql, params))
    finally:
        connection.close()


@dataclass
class Api:
    client: TestClient
    db_path: Path
    settings: Settings

    def headers(self, email: str | None = None, scheme: str = "Bearer") -> dict[str, str]:
        token = issue_token(self.settings.app_secret, email or self.settings.hr_email)
        return {"Authorization": f"{scheme} {token}"}


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    db_path = tmp_path / "comppulse.db"
    settings = Settings(
        database_url=_sqlite_url(db_path),
        seed_count=0,
        app_secret="test-secret",
        hr_email="hr@acme.test",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        _seed(db_path)
        yield Api(client, db_path, settings)


def _create(api: Api, **overrides: object) -> dict[str, object]:
    response = api.client.post("/employees", headers=api.headers(), json=_body(**overrides))
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict)
    return body


def test_post_employee_assigns_currency_number_and_usd(api: Api) -> None:
    created = _create(api, status="terminated", level="M2", department_id=2)
    uuid.UUID(str(created["id"]))
    assert created == {
        "id": created["id"],
        "employee_number": "EMP-00001",
        "first_name": "Ada",
        "last_name": "Okoye",
        "email": "ada.okoye@acme.test",
        "job_title": "Software Engineer",
        "department": {"id": 2, "name": "Sales"},
        "country": {"code": "US", "name": "United States"},
        "currency_code": "USD",
        "level": "M2",
        "base_salary_scaled": "15500000",
        "variable_pay_scaled": "0",
        "salary_scale": 2,
        "salary_usd_scaled": "15500000",
        "salary_usd_scale": 2,
        "status": "terminated",
        "hire_date": "2026-01-15",
        "comp_effective_date": "2026-01-15",
        "version_id": 1,
    }
    second = _create(api, email="grace@acme.test", first_name="Grace")
    assert second["employee_number"] == "EMP-00002"
    assert second["version_id"] == 1
    rows = _query(
        api.db_path,
        "SELECT employee_number FROM employees_fts WHERE employees_fts MATCH ?",
        ("ada",),
    )
    assert rows == [("EMP-00001",)]


def test_employee_number_uses_max_and_widens_past_five_digits(api: Api) -> None:
    _insert_employee(api.db_path, "gap-a", "EMP-00007", "gap.a@acme.test")
    _insert_employee(api.db_path, "gap-b", "EMP-00009", "gap.b@acme.test")
    created = _create(api)
    assert created["employee_number"] == "EMP-00010"

    _insert_employee(api.db_path, "wide", "EMP-99999", "wide@acme.test")
    widened = _create(api, email="wide.next@acme.test")
    assert widened["employee_number"] == "EMP-100000"


def test_post_duplicate_email_is_conflict(api: Api) -> None:
    _create(api)
    response = api.client.post("/employees", headers=api.headers(), json=_body())
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Email already exists"
    assert _query(api.db_path, "SELECT COUNT(*) FROM employees") == [(1,)]


def test_post_duplicate_employee_number_is_conflict(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create(api)

    async def _fixed(_session: object) -> str:
        return "EMP-00001"

    monkeypatch.setattr("app.compensation._next_employee_number", _fixed)
    response = api.client.post(
        "/employees",
        headers=api.headers(),
        json=_body(email="other@acme.test"),
    )
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "Employee number already exists"}
    assert _query(api.db_path, "SELECT COUNT(*) FROM employees") == [(1,)]


def test_concurrent_creates_all_succeed_with_distinct_numbers(api: Api) -> None:
    def _post(index: int) -> int:
        body = _body(email=f"race.{index}@acme.test")
        return api.client.post("/employees", headers=api.headers(), json=body).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(_post, range(8)))
    assert statuses == [200] * 8
    numbers = _query(api.db_path, "SELECT employee_number FROM employees")
    assert len({number for (number,) in numbers}) == 8


def test_post_unknown_department_or_country_is_422(api: Api) -> None:
    department = api.client.post(
        "/employees", headers=api.headers(), json=_body(department_id=99)
    )
    assert department.status_code == 422, department.text
    assert department.json() == {"detail": "Unknown department"}
    country = api.client.post(
        "/employees", headers=api.headers(), json=_body(country_code="ZZ")
    )
    assert country.status_code == 422, country.text
    assert country.json() == {"detail": "Unknown country"}
    assert _query(api.db_path, "SELECT COUNT(*) FROM employees") == [(0,)]


@pytest.mark.parametrize(
    "overrides",
    [
        {"level": "IC6"},
        {"level": "ic3"},
        {"status": "Active"},
        {"status": "leave"},
        {"base_salary_scaled": "12.00"},
        {"base_salary_scaled": "1e5"},
        {"variable_pay_scaled": "1E5"},
        {"base_salary_scaled": "+100"},
        {"base_salary_scaled": ""},
        {"base_salary_scaled": " 100"},
        {"base_salary_scaled": "9223372036854775808"},
        {"currency_code": "EUR"},
        {"first_name": ""},
        {"first_name": "   "},
        {"job_title": "\t"},
        {"email": "not-an-email"},
        {"email": "a@b"},
        {"email": "a b@acme.test"},
        {"bonus": "1"},
    ],
)
def test_post_rejects_invalid_body(api: Api, overrides: dict[str, object]) -> None:
    response = api.client.post("/employees", headers=api.headers(), json=_body(**overrides))
    assert response.status_code == 422, response.text


def test_post_trims_surrounding_whitespace(api: Api) -> None:
    response = api.client.post(
        "/employees",
        headers=api.headers(),
        json=_body(first_name=" Ada ", email=" ada.trim@acme.test "),
    )
    assert response.status_code in (200, 201), response.text
    assert response.json()["first_name"] == "Ada"
    assert response.json()["email"] == "ada.trim@acme.test"


def test_post_rejects_numeric_salary(api: Api) -> None:
    body = _body()
    body["base_salary_scaled"] = 15500000
    response = api.client.post("/employees", headers=api.headers(), json=body)
    assert response.status_code == 422, response.text


def test_post_converts_jpy_after_summing_local_amounts(api: Api) -> None:
    created = _create(
        api,
        email="yuki@acme.test",
        country_code="JP",
        base_salary_scaled="50",
        variable_pay_scaled="50",
    )
    assert created["currency_code"] == "JPY"
    assert created["salary_scale"] == 0
    assert created["salary_usd_scaled"] == _expected_usd("50", "50", 0, "149000000")
    assert created["salary_usd_scaled"] == "67"
    one_side = decimal_to_scaled(
        scaled_to_decimal("50", 0) / scaled_to_decimal("149000000", 6),
        2,
    )
    rounded_apart = decimal_to_scaled(
        scaled_to_decimal(one_side, 2) + scaled_to_decimal(one_side, 2),
        2,
    )
    assert rounded_apart == "68"

    gbp = _create(
        api,
        email="ada.gb@acme.test",
        country_code="GB",
        base_salary_scaled="10000",
        variable_pay_scaled="0",
    )
    assert gbp["salary_usd_scaled"] == _expected_usd("10000", "0", 2, "780000")
    assert gbp["salary_scale"] == 2


def test_post_allows_negative_salary_digits(api: Api) -> None:
    created = _create(api, base_salary_scaled="-10000", variable_pay_scaled="0")
    assert created["base_salary_scaled"] == "-10000"
    assert created["salary_usd_scaled"] == "-10000"


def test_routes_require_hr_token(api: Api) -> None:
    unauthenticated = api.client.post("/employees", json=_body())
    assert unauthenticated.status_code == 401
    assert unauthenticated.json() == {"detail": "Not authenticated"}
    assert _query(api.db_path, "SELECT COUNT(*) FROM employees") == [(0,)]

    created = _create(api)
    employee_id = str(created["id"])
    cases = [
        ("post", "/employees", _body(email="other@acme.test")),
        ("patch", f"/employees/{employee_id}/compensation", _comp()),
        ("get", f"/employees/{employee_id}/audit", None),
        ("get", "/fx", None),
        ("patch", "/fx/USD", {"units_per_usd_scaled": "2000000"}),
    ]
    for method, path, payload in cases:
        kwargs: dict[str, object] = {}
        if payload is not None:
            kwargs["json"] = payload
        response = getattr(api.client, method)(path, **kwargs)
        assert response.status_code == 401, (method, path, response.text)
        bad = getattr(api.client, method)(
            path,
            headers={"Authorization": "Bearer nope"},
            **kwargs,
        )
        assert bad.status_code == 401, (method, path, bad.text)
        other = getattr(api.client, method)(
            path,
            headers=api.headers("other@acme.test"),
            **kwargs,
        )
        assert other.status_code == 401, (method, path, other.text)

    lowercase = api.client.get("/fx", headers=api.headers(scheme="bearer"))
    assert lowercase.status_code == 200, lowercase.text


def test_compensation_bumps_version_and_writes_audit(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.compensation.utc_timestamp", lambda: "2026-04-01T09:00:00Z")
    created = _create(api, base_salary_scaled="10000", variable_pay_scaled="0")
    response = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(
            base_salary_scaled="20000",
            variable_pay_scaled="500",
            version_id=1,
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version_id"] == 2
    assert body["base_salary_scaled"] == "20000"
    assert body["variable_pay_scaled"] == "500"
    assert body["salary_usd_scaled"] == "20500"
    assert body["salary_scale"] == 2
    assert body["comp_effective_date"] == "2026-04-01"
    assert body["hire_date"] == "2026-01-15"
    assert body["employee_number"] == "EMP-00001"
    assert _query(
        api.db_path,
        "SELECT updated_at FROM employees WHERE id = ?",
        (created["id"],),
    ) == [("2026-04-01T09:00:00Z",)]

    audit = api.client.get(f"/employees/{created['id']}/audit", headers=api.headers())
    assert audit.status_code == 200, audit.text
    assert audit.json() == {
        "items": [
            {
                "id": 1,
                "previous_base_salary_scaled": "10000",
                "new_base_salary_scaled": "20000",
                "previous_variable_pay_scaled": "0",
                "new_variable_pay_scaled": "500",
                "salary_scale": 2,
                "currency_code": "USD",
                "fx_units_per_usd_scaled": "1000000",
                "fx_scale": 6,
                "previous_salary_usd_scaled": "10000",
                "new_salary_usd_scaled": "20500",
                "salary_usd_scale": 2,
                "reason": "Annual review",
                "effective_date": "2026-04-01",
                "changed_by": "hr@acme.test",
                "created_at": "2026-04-01T09:00:00Z",
            }
        ]
    }


def test_same_salary_still_bumps_version(api: Api) -> None:
    created = _create(api, base_salary_scaled="10000", variable_pay_scaled="0")
    response = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="10000", variable_pay_scaled="0", version_id=1),
    )
    assert response.status_code == 200, response.text
    assert response.json()["version_id"] == 2
    assert _query(api.db_path, "SELECT COUNT(*) FROM compensation_audit_logs") == [(1,)]


def test_stale_version_is_409_and_writes_nothing(api: Api) -> None:
    created = _create(api, base_salary_scaled="10000")
    first = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="20000", version_id=1, reason="First"),
    )
    assert first.status_code == 200, first.text
    stale = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="30000", version_id=1, reason="Stale"),
    )
    assert stale.status_code == 409, stale.text
    assert stale.json() == {"detail": "Record was modified. Reload and try again."}
    assert _query(
        api.db_path,
        "SELECT base_salary_scaled, version_id FROM employees WHERE id = ?",
        (created["id"],),
    ) == [("20000", 2)]
    reasons = _query(api.db_path, "SELECT reason FROM compensation_audit_logs")
    assert reasons == [("First",)]
    print(f"409 detail={stale.json()['detail']} audit_reasons={reasons}")


def test_compensation_missing_employee_is_404(api: Api) -> None:
    response = api.client.patch(
        "/employees/missing-id/compensation",
        headers=api.headers(),
        json=_comp(),
    )
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Employee not found"}
    assert _query(api.db_path, "SELECT COUNT(*) FROM compensation_audit_logs") == [(0,)]


def test_audit_is_newest_first_and_scoped_to_the_employee(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    ada = _create(api, base_salary_scaled="10000")
    grace = _create(api, email="grace@acme.test", base_salary_scaled="10000")
    empty = api.client.get(f"/employees/{grace['id']}/audit", headers=api.headers())
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"items": []}
    missing = api.client.get("/employees/missing-id/audit", headers=api.headers())
    assert missing.status_code == 404, missing.text
    assert missing.json() == {"detail": "Employee not found"}

    stamps = iter(["2026-04-01T09:00:00Z", "2026-05-01T09:00:00Z", "2026-06-01T09:00:00Z"])
    monkeypatch.setattr("app.compensation.utc_timestamp", lambda: next(stamps))
    first = api.client.patch(
        f"/employees/{ada['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="11000", version_id=1, reason="First"),
    )
    assert first.status_code == 200, first.text
    second = api.client.patch(
        f"/employees/{ada['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="12000", version_id=2, reason="Second"),
    )
    assert second.status_code == 200, second.text
    other = api.client.patch(
        f"/employees/{grace['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="13000", version_id=1, reason="Grace only"),
    )
    assert other.status_code == 200, other.text

    ada_audit = api.client.get(f"/employees/{ada['id']}/audit", headers=api.headers())
    assert ada_audit.status_code == 200, ada_audit.text
    items = ada_audit.json()["items"]
    assert [item["reason"] for item in items] == ["Second", "First"]
    assert [item["created_at"] for item in items] == [
        "2026-05-01T09:00:00Z",
        "2026-04-01T09:00:00Z",
    ]
    assert items[0]["id"] > items[1]["id"]
    grace_audit = api.client.get(f"/employees/{grace['id']}/audit", headers=api.headers())
    assert [item["reason"] for item in grace_audit.json()["items"]] == ["Grace only"]


def test_jpy_audit_uses_currency_scale(api: Api) -> None:
    created = _create(
        api,
        email="yuki@acme.test",
        country_code="JP",
        base_salary_scaled="14900000",
        variable_pay_scaled="0",
    )
    assert created["salary_usd_scaled"] == "10000000"
    response = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="29800000", variable_pay_scaled="0", version_id=1),
    )
    assert response.status_code == 200, response.text
    assert response.json()["salary_scale"] == 0
    assert response.json()["salary_usd_scaled"] == "20000000"
    item = api.client.get(
        f"/employees/{created['id']}/audit", headers=api.headers()
    ).json()["items"][0]
    assert item["salary_scale"] == 0
    assert item["fx_scale"] == 6
    assert item["salary_usd_scale"] == 2
    assert item["fx_units_per_usd_scaled"] == "149000000"
    assert item["previous_salary_usd_scaled"] == "10000000"
    assert item["new_salary_usd_scaled"] == "20000000"


@pytest.mark.parametrize(
    "payload",
    [
        {"reason": ""},
        {"reason": "   "},
        {"base_salary_scaled": "12.00"},
        {"base_salary_scaled": "1e5"},
        {"note": "nope"},
    ],
)
def test_compensation_rejects_invalid_body(api: Api, payload: dict[str, object]) -> None:
    created = _create(api)
    response = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(**payload),
    )
    assert response.status_code == 422, response.text
    assert _query(api.db_path, "SELECT COUNT(*) FROM compensation_audit_logs") == [(0,)]


def test_compensation_rolls_back_when_audit_insert_fails(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = _create(api, base_salary_scaled="10000")

    async def _boom(_session: object, _values: object) -> None:
        raise RuntimeError("fail audit")

    monkeypatch.setattr("app.compensation._insert_audit", _boom)
    with pytest.raises(RuntimeError, match="fail audit"):
        api.client.patch(
            f"/employees/{created['id']}/compensation",
            headers=api.headers(),
            json=_comp(base_salary_scaled="20000", version_id=1),
        )
    assert _query(
        api.db_path,
        "SELECT base_salary_scaled, salary_usd_scaled, version_id FROM employees WHERE id = ?",
        (created["id"],),
    ) == [("10000", "10000", 1)]
    assert _query(api.db_path, "SELECT COUNT(*) FROM compensation_audit_logs") == [(0,)]
    audit = api.client.get(f"/employees/{created['id']}/audit", headers=api.headers())
    assert audit.status_code == 200, audit.text
    assert audit.json() == {"items": []}


def test_audit_log_rejects_update_and_delete(api: Api) -> None:
    created = _create(api)
    patched = api.client.patch(
        f"/employees/{created['id']}/compensation",
        headers=api.headers(),
        json=_comp(reason="Annual review"),
    )
    assert patched.status_code == 200, patched.text
    connection = sqlite3.connect(api.db_path)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        assert connection.execute("SELECT COUNT(*) FROM compensation_audit_logs").fetchone() == (
            1,
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE compensation_audit_logs SET reason = 'changed'")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM compensation_audit_logs")
        connection.rollback()
        assert connection.execute("SELECT reason FROM compensation_audit_logs").fetchone() == (
            "Annual review",
        )
    finally:
        connection.close()


def test_get_fx_returns_reference_currency_shape(api: Api) -> None:
    response = api.client.get("/fx", headers=api.headers())
    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "code": "GBP",
            "name": "British Pound",
            "minor_scale": 2,
            "units_per_usd_scaled": "780000",
            "units_per_usd_scale": 6,
        },
        {
            "code": "INR",
            "name": "Indian Rupee",
            "minor_scale": 2,
            "units_per_usd_scaled": "83500000",
            "units_per_usd_scale": 6,
        },
        {
            "code": "JPY",
            "name": "Japanese Yen",
            "minor_scale": 0,
            "units_per_usd_scaled": "149000000",
            "units_per_usd_scale": 6,
        },
        {
            "code": "USD",
            "name": "US Dollar",
            "minor_scale": 2,
            "units_per_usd_scaled": "1000000",
            "units_per_usd_scale": 6,
        },
    ]


def test_fx_recompute_does_not_rewrite_audit_snapshots(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    usd = _create(api, base_salary_scaled="15500000", variable_pay_scaled="0")
    jpy = _create(
        api,
        email="yuki@acme.test",
        country_code="JP",
        base_salary_scaled="14900000",
        variable_pay_scaled="0",
    )
    inr = _create(
        api,
        email="ada.in@acme.test",
        country_code="IN",
        base_salary_scaled="83500000",
        variable_pay_scaled="0",
        status="terminated",
    )
    assert usd["salary_usd_scaled"] == "15500000"
    assert jpy["salary_usd_scaled"] == "10000000"
    assert inr["salary_usd_scaled"] == "1000000"

    usd_patch = api.client.patch(
        f"/employees/{usd['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="16000000", version_id=1, reason="USD review"),
    )
    assert usd_patch.status_code == 200, usd_patch.text
    assert usd_patch.json()["version_id"] == 2
    assert usd_patch.json()["salary_usd_scaled"] == "16000000"
    inr_patch = api.client.patch(
        f"/employees/{inr['id']}/compensation",
        headers=api.headers(),
        json=_comp(base_salary_scaled="83500000", version_id=1, reason="INR review"),
    )
    assert inr_patch.status_code == 200, inr_patch.text
    before_usd_audit = api.client.get(
        f"/employees/{usd['id']}/audit", headers=api.headers()
    ).json()
    before_inr_audit = api.client.get(
        f"/employees/{inr['id']}/audit", headers=api.headers()
    ).json()
    usd_updated_at = _query(
        api.db_path, "SELECT updated_at FROM employees WHERE id = ?", (usd["id"],)
    )
    inr_updated_at = _query(
        api.db_path, "SELECT updated_at FROM employees WHERE id = ?", (inr["id"],)
    )
    monkeypatch.setattr("app.compensation.utc_timestamp", lambda: "2026-08-01T00:00:00Z")

    fx = api.client.patch(
        "/fx/USD",
        headers=api.headers(),
        json={"units_per_usd_scaled": "2000000"},
    )
    assert fx.status_code == 200, fx.text
    assert fx.json() == {
        "code": "USD",
        "name": "US Dollar",
        "minor_scale": 2,
        "units_per_usd_scaled": "2000000",
        "units_per_usd_scale": 6,
    }
    assert _query(
        api.db_path,
        "SELECT salary_usd_scaled, base_salary_scaled, version_id, updated_at "
        "FROM employees WHERE id = ?",
        (usd["id"],),
    ) == [("8000000", "16000000", 2, usd_updated_at[0][0])]
    assert _query(
        api.db_path,
        "SELECT salary_usd_scaled, version_id FROM employees WHERE id = ?",
        (jpy["id"],),
    ) == [("10000000", 1)]
    assert api.client.get(f"/employees/{usd['id']}/audit", headers=api.headers()).json() == (
        before_usd_audit
    )
    assert _query(
        api.db_path,
        "SELECT updated_at, units_per_usd_scaled FROM currencies WHERE code = 'USD'",
    ) == [("2026-08-01T00:00:00Z", "2000000")]

    inr_fx = api.client.patch(
        "/fx/INR",
        headers=api.headers(),
        json={"units_per_usd_scaled": "167000000"},
    )
    assert inr_fx.status_code == 200, inr_fx.text
    assert _query(
        api.db_path,
        "SELECT salary_usd_scaled, version_id, base_salary_scaled FROM employees WHERE id = ?",
        (inr["id"],),
    ) == [("500000", 2, "83500000")]
    assert api.client.get(f"/employees/{inr['id']}/audit", headers=api.headers()).json() == (
        before_inr_audit
    )
    assert _query(
        api.db_path,
        "SELECT salary_usd_scaled, updated_at FROM employees WHERE id = ?",
        (usd["id"],),
    ) == [("8000000", usd_updated_at[0][0])]
    assert _query(
        api.db_path,
        "SELECT updated_at FROM employees WHERE id = ?",
        (inr["id"],),
    ) == inr_updated_at


def test_fx_unknown_code_and_invalid_rate(api: Api) -> None:
    missing = api.client.patch(
        "/fx/XXX",
        headers=api.headers(),
        json={"units_per_usd_scaled": "1000000"},
    )
    assert missing.status_code == 404, missing.text
    assert missing.json() == {"detail": "Currency not found"}
    for bad in ("12.00", "1e5", "0", "-0", "-5000000", "", "1000000.0", "+1000000"):
        response = api.client.patch(
            "/fx/USD",
            headers=api.headers(),
            json={"units_per_usd_scaled": bad},
        )
        assert response.status_code == 422, (bad, response.text)
    extra = api.client.patch(
        "/fx/USD",
        headers=api.headers(),
        json={"units_per_usd_scaled": "1000000", "name": "Nope"},
    )
    assert extra.status_code == 422, extra.text
    lowercase = api.client.patch(
        "/fx/usd",
        headers=api.headers(),
        json={"units_per_usd_scaled": "2000000"},
    )
    assert lowercase.status_code == 404, lowercase.text
    assert _query(
        api.db_path,
        "SELECT units_per_usd_scaled FROM currencies WHERE code = 'USD'",
    ) == [("1000000",)]
