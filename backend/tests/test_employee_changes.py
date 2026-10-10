import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.deps import issue_token
from app.main import create_app
from app.settings import Settings


def _sqlite_url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


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
            ],
        )
        connection.executemany(
            "INSERT INTO countries (code, name, currency_code) VALUES (?, ?, ?)",
            [("US", "United States", "USD"), ("GB", "United Kingdom", "GBP")],
        )
        connection.executemany(
            "INSERT INTO departments (id, name) VALUES (?, ?)",
            [(1, "Engineering"), (2, "Sales")],
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

    def headers(self) -> dict[str, str]:
        token = issue_token(self.settings.app_secret, self.settings.hr_email)
        return {"Authorization": f"Bearer {token}"}


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


def _edit(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "reason": "Promotion",
        "effective_date": "2026-05-01",
        "version_id": 1,
    }
    if not overrides.keys() & {
        "first_name",
        "last_name",
        "email",
        "job_title",
        "department_id",
        "level",
    }:
        payload["job_title"] = "Staff Engineer"
    payload.update(overrides)
    return payload


def _status(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "terminated",
        "reason": "Resigned",
        "effective_date": "2026-06-30",
        "version_id": 1,
    }
    payload.update(overrides)
    return payload


def _changes(api: Api, employee_id: object) -> list[dict[str, object]]:
    response = api.client.get(f"/employees/{employee_id}/changes", headers=api.headers())
    assert response.status_code == 200, response.text
    return response.json()["items"]


@pytest.mark.parametrize(
    ("field", "value", "previous"),
    [
        ("first_name", "Adaeze", "Ada"),
        ("last_name", "Obi", "Okoye"),
        ("email", "adaeze@acme.test", "ada.okoye@acme.test"),
        ("job_title", "Staff Engineer", "Software Engineer"),
        ("department_id", 2, "1"),
        ("level", "M1", "IC3"),
    ],
)
def test_patch_each_field(api: Api, field: str, value: object, previous: str) -> None:
    created = _create(api)
    response = api.client.patch(
        f"/employees/{created['id']}", headers=api.headers(), json=_edit(**{field: value})
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version_id"] == 2
    if field == "department_id":
        assert body["department"] == {"id": 2, "name": "Sales"}
    else:
        assert body[field] == value
    fetched = api.client.get(f"/employees/{created['id']}", headers=api.headers())
    assert fetched.json() == body
    items = _changes(api, created["id"])
    assert len(items) == 1
    assert items[0]["field"] == field
    assert items[0]["previous_value"] == previous
    assert items[0]["new_value"] == str(value)
    assert items[0]["reason"] == "Promotion"
    assert items[0]["effective_date"] == "2026-05-01"
    assert items[0]["changed_by"] == "hr@acme.test"


def test_patch_logs_only_changed_fields_and_keeps_search_in_sync(api: Api) -> None:
    created = _create(api)
    response = api.client.patch(
        f"/employees/{created['id']}",
        headers=api.headers(),
        json=_edit(first_name="Ada", last_name="Obi", job_title="  Principal  "),
    )
    assert response.status_code == 200, response.text
    assert response.json()["job_title"] == "Principal"
    assert sorted(item["field"] for item in _changes(api, created["id"])) == [
        "job_title",
        "last_name",
    ]
    rows = _query(
        api.db_path,
        "SELECT employee_number FROM employees_fts WHERE employees_fts MATCH ?",
        ("obi",),
    )
    assert rows == [("EMP-00001",)]


def test_patch_without_any_change_writes_nothing(api: Api) -> None:
    created = _create(api)
    url = f"/employees/{created['id']}"
    same = _edit(job_title="Software Engineer")
    response = api.client.patch(url, headers=api.headers(), json=same)
    assert response.status_code == 200, response.text
    assert response.json() == created
    assert _changes(api, created["id"]) == []
    stale = api.client.patch(url, headers=api.headers(), json={**same, "version_id": 7})
    assert stale.status_code == 409, stale.text


def test_patch_stale_version_is_conflict_and_writes_nothing(api: Api) -> None:
    created = _create(api)
    url = f"/employees/{created['id']}"
    first = api.client.patch(url, headers=api.headers(), json=_edit())
    assert first.status_code == 200, first.text
    stale = api.client.patch(
        url, headers=api.headers(), json=_edit(job_title="Other", level="M1")
    )
    assert stale.status_code == 409, stale.text
    assert stale.json() == {"detail": "Record was modified. Reload and try again."}
    assert _query(
        api.db_path,
        "SELECT job_title, level, version_id FROM employees WHERE id = ?",
        (created["id"],),
    ) == [("Staff Engineer", "IC3", 2)]
    assert len(_changes(api, created["id"])) == 1


def test_patch_duplicate_email_is_conflict(api: Api) -> None:
    _create(api)
    other = _create(api, email="grace@acme.test")
    response = api.client.patch(
        f"/employees/{other['id']}",
        headers=api.headers(),
        json=_edit(email="ada.okoye@acme.test"),
    )
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "Email already exists"}
    assert _changes(api, other["id"]) == []
    assert _query(
        api.db_path, "SELECT version_id FROM employees WHERE id = ?", (other["id"],)
    ) == [(1,)]


def test_patch_unknown_department_is_422(api: Api) -> None:
    created = _create(api)
    response = api.client.patch(
        f"/employees/{created['id']}", headers=api.headers(), json=_edit(department_id=99)
    )
    assert response.status_code == 422, response.text
    assert response.json() == {"detail": "Unknown department"}
    assert _changes(api, created["id"]) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"first_name": ""},
        {"last_name": "   "},
        {"job_title": "\t"},
        {"email": "not-an-email"},
        {"level": "IC6"},
        {"level": "ic3"},
        {"first_name": None},
        {"reason": ""},
        {"reason": "   "},
        {"country_code": "GB"},
        {"currency_code": "GBP"},
        {"base_salary_scaled": "1"},
        {"status": "terminated"},
        {"bonus": "1"},
        {"effective_date": "not-a-date"},
        {"version_id": "x"},
    ],
)
def test_patch_rejects_invalid_body(api: Api, overrides: dict[str, object]) -> None:
    created = _create(api)
    response = api.client.patch(
        f"/employees/{created['id']}", headers=api.headers(), json=_edit(**overrides)
    )
    assert response.status_code == 422, response.text
    assert _changes(api, created["id"]) == []


def test_patch_requires_a_field_and_the_lock_inputs(api: Api) -> None:
    created = _create(api)
    url = f"/employees/{created['id']}"
    empty = {"reason": "Fix", "effective_date": "2026-05-01", "version_id": 1}
    assert api.client.patch(url, headers=api.headers(), json=empty).status_code == 422
    for missing in ("reason", "effective_date", "version_id"):
        body = _edit()
        del body[missing]
        assert api.client.patch(url, headers=api.headers(), json=body).status_code == 422


def test_post_status_terminates_and_reactivates(api: Api) -> None:
    created = _create(api)
    url = f"/employees/{created['id']}/status"
    ended = api.client.post(url, headers=api.headers(), json=_status())
    assert ended.status_code == 200, ended.text
    assert ended.json()["status"] == "terminated"
    assert ended.json()["version_id"] == 2
    back = api.client.post(
        url,
        headers=api.headers(),
        json=_status(status="active", reason="Rehired", version_id=2),
    )
    assert back.status_code == 200, back.text
    assert back.json()["status"] == "active"
    assert back.json()["version_id"] == 3
    items = _changes(api, created["id"])
    assert [(i["field"], i["previous_value"], i["new_value"], i["reason"]) for i in items] == [
        ("status", "terminated", "active", "Rehired"),
        ("status", "active", "terminated", "Resigned"),
    ]


def test_post_status_same_status_is_conflict(api: Api) -> None:
    created = _create(api)
    response = api.client.post(
        f"/employees/{created['id']}/status",
        headers=api.headers(),
        json=_status(status="active"),
    )
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "Employee is already active"}
    assert _changes(api, created["id"]) == []


def test_post_status_stale_version_is_conflict(api: Api) -> None:
    created = _create(api)
    response = api.client.post(
        f"/employees/{created['id']}/status",
        headers=api.headers(),
        json=_status(version_id=5),
    )
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "Record was modified. Reload and try again."}
    assert _query(
        api.db_path, "SELECT status, version_id FROM employees WHERE id = ?", (created["id"],)
    ) == [("active", 1)]
    assert _changes(api, created["id"]) == []


@pytest.mark.parametrize(
    "overrides",
    [{"status": "leave"}, {"status": "Active"}, {"reason": " "}, {"hire_date": "2026-01-01"}],
)
def test_post_status_rejects_invalid_body(api: Api, overrides: dict[str, object]) -> None:
    created = _create(api)
    response = api.client.post(
        f"/employees/{created['id']}/status", headers=api.headers(), json=_status(**overrides)
    )
    assert response.status_code == 422, response.text


def test_terminated_employee_leaves_active_analytics(api: Api) -> None:
    first = _create(api)
    _create(api, email="grace@acme.test")
    before = api.client.get("/analytics/overview", headers=api.headers()).json()
    assert before["headcount"] == 2
    ended = api.client.post(
        f"/employees/{first['id']}/status", headers=api.headers(), json=_status()
    )
    assert ended.status_code == 200, ended.text
    after = api.client.get("/analytics/overview", headers=api.headers()).json()
    assert after["headcount"] == 1
    listed = api.client.get("/employees?status=active", headers=api.headers()).json()
    assert listed["total"] == 1


def test_change_log_rejects_update_and_delete(api: Api) -> None:
    created = _create(api)
    patched = api.client.patch(
        f"/employees/{created['id']}", headers=api.headers(), json=_edit()
    )
    assert patched.status_code == 200, patched.text
    connection = sqlite3.connect(api.db_path)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE employee_change_logs SET reason = 'changed'")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM employee_change_logs")
        connection.rollback()
        assert connection.execute("SELECT reason FROM employee_change_logs").fetchone() == (
            "Promotion",
        )
    finally:
        connection.close()


def test_changes_are_newest_first_with_full_shape(api: Api) -> None:
    created = _create(api)
    api.client.patch(f"/employees/{created['id']}", headers=api.headers(), json=_edit())
    api.client.post(
        f"/employees/{created['id']}/status",
        headers=api.headers(),
        json=_status(version_id=2),
    )
    items = _changes(api, created["id"])
    assert [item["field"] for item in items] == ["status", "job_title"]
    assert items[0].keys() == {
        "id",
        "field",
        "previous_value",
        "new_value",
        "reason",
        "effective_date",
        "changed_by",
        "created_at",
    }
    assert items[0]["id"] > items[1]["id"]


def test_change_routes_require_token(api: Api) -> None:
    created = _create(api)
    url = f"/employees/{created['id']}"
    assert api.client.patch(url, json=_edit()).status_code == 401
    assert api.client.post(f"{url}/status", json=_status()).status_code == 401
    assert api.client.get(f"{url}/changes").status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert api.client.patch(url, headers=bad, json=_edit()).status_code == 401


def test_change_routes_missing_employee_is_404(api: Api) -> None:
    url = "/employees/missing"
    patched = api.client.patch(url, headers=api.headers(), json=_edit())
    assert patched.status_code == 404, patched.text
    assert patched.json() == {"detail": "Employee not found"}
    posted = api.client.post(f"{url}/status", headers=api.headers(), json=_status())
    assert posted.status_code == 404, posted.text
    got = api.client.get(f"{url}/changes", headers=api.headers())
    assert got.status_code == 404, got.text


def test_concurrent_patches_with_same_version_one_wins(api: Api) -> None:
    created = _create(api)

    def _patch(index: int) -> int:
        return api.client.patch(
            f"/employees/{created['id']}",
            headers=api.headers(),
            json=_edit(job_title=f"Title {index}"),
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(_patch, range(8)))
    assert sorted(statuses) == [200] + [409] * 7
    assert len(_changes(api, created["id"])) == 1
    assert _query(
        api.db_path, "SELECT version_id FROM employees WHERE id = ?", (created["id"],)
    ) == [(2,)]
