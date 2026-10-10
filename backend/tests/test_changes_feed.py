# ruff: noqa: F401, F811
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_employee_changes import Api, _create, _edit, _status, api

from app.directory import sign_cursor

_CHANGE_SQL = """
INSERT INTO employee_change_logs (
  employee_id, field, previous_value, new_value, reason, effective_date, changed_by, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

_Row = tuple[str, str, str | None, str | None, str, str, str, str]


def _change(
    employee_id: str,
    created_at: str,
    *,
    field: str = "level",
    previous: str | None = "IC3",
    new: str | None = "IC4",
    effective_date: str = "2026-01-01",
    changed_by: str = "hr@acme.test",
    reason: str = "Review",
) -> _Row:
    return (employee_id, field, previous, new, reason, effective_date, changed_by, created_at)


def _insert(db_path: Path, rows: list[_Row]) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.executemany(_CHANGE_SQL, rows)
        connection.commit()
    finally:
        connection.close()


def _two_employees(api: Api) -> tuple[str, str]:
    ada = _create(api)
    bola = _create(
        api,
        first_name="Bola",
        last_name="Ade",
        email="bola.ade@acme.test",
        department_id=2,
    )
    return str(ada["id"]), str(bola["id"])


def _walk(api: Api, **params: object) -> list[int]:
    ids: list[int] = []
    cursor = None
    while True:
        page_params = {**params, "cursor": cursor} if cursor else params
        response = api.client.get("/changes", params=page_params, headers=api.headers())
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == {"items", "next_cursor"}
        ids.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return ids


def test_newest_first_with_employee_context(api: Api) -> None:
    ada, bola = _two_employees(api)
    _insert(
        api.db_path,
        [
            _change(ada, "2026-01-01T09:00:00Z"),
            _change(bola, "2026-03-01T09:00:00Z", reason="Promotion"),
            _change(ada, "2026-02-01T09:00:00Z"),
        ],
    )
    body = api.client.get("/changes", headers=api.headers()).json()
    assert [item["id"] for item in body["items"]] == [2, 3, 1]
    assert body["next_cursor"] is None
    assert body["items"][0] == {
        "id": 2,
        "employee_id": bola,
        "employee_number": body["items"][0]["employee_number"],
        "employee_name": "Bola Ade",
        "department": {"id": 2, "name": "Sales"},
        "field": "level",
        "previous_value": "IC3",
        "new_value": "IC4",
        "previous_label": None,
        "new_label": None,
        "reason": "Promotion",
        "effective_date": "2026-01-01",
        "changed_by": "hr@acme.test",
        "created_at": "2026-03-01T09:00:00Z",
    }


def test_empty_feed(api: Api) -> None:
    body = api.client.get("/changes", headers=api.headers()).json()
    assert body == {"items": [], "next_cursor": None}


def test_pagination_with_shared_timestamps(api: Api) -> None:
    ada, bola = _two_employees(api)
    stamps = ["2026-01-01T09:00:00Z", "2026-01-02T09:00:00Z", "2026-01-02T09:00:00Z"]
    _insert(
        api.db_path,
        [_change(ada if i % 2 else bola, stamps[i % 3]) for i in range(37)],
    )
    everything = api.client.get("/changes", params={"limit": 100}, headers=api.headers())
    unpaged = [item["id"] for item in everything.json()["items"]]
    assert len(unpaged) == 37
    for limit in (1, 2, 5, 36, 37):
        walked = _walk(api, limit=limit)
        assert walked == unpaged
        assert len(set(walked)) == 37


def test_default_limit_is_50(api: Api) -> None:
    ada, _ = _two_employees(api)
    _insert(api.db_path, [_change(ada, f"2026-01-01T09:00:{i % 60:02d}Z") for i in range(51)])
    body = api.client.get("/changes", headers=api.headers()).json()
    assert len(body["items"]) == 50
    assert body["next_cursor"] is not None


def test_filters(api: Api) -> None:
    ada, bola = _two_employees(api)
    _insert(
        api.db_path,
        [
            _change(ada, "2026-01-01T09:00:00Z", effective_date="2026-01-10", field="level"),
            _change(
                bola,
                "2026-01-02T09:00:00Z",
                effective_date="2026-02-10",
                field="job_title",
                changed_by="x@a",
            ),
            _change(
                ada,
                "2026-01-03T09:00:00Z",
                effective_date="2026-03-10",
                field="status",
                changed_by="x@a",
            ),
        ],
    )

    def ids(**params: object) -> list[int]:
        response = api.client.get("/changes", params=params, headers=api.headers())
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert ids(employee_id=ada) == [3, 1]
    assert ids(employee_id="missing") == []
    assert ids(department_id=2) == [2]
    assert ids(field="level") == [1]
    assert ids(field="status") == [3]
    assert ids(since="2026-02-10") == [3, 2]
    assert ids(until="2026-02-10") == [2, 1]
    assert ids(since="2026-02-01", until="2026-02-28") == [2]
    assert ids(changed_by="x@a") == [3, 2]
    assert ids(changed_by="x@a", employee_id=ada, since="2026-03-10") == [3]
    assert ids(changed_by="x@a", field="job_title", department_id=2) == [2]
    assert ids(changed_by="x@a", field="level") == []
    assert _walk(api, changed_by="x@a", limit=1) == [3, 2]
    assert _walk(api, field="level", limit=1) == [1]


def test_department_labels(api: Api) -> None:
    ada, _ = _two_employees(api)
    _insert(
        api.db_path,
        [
            _change(ada, "2026-01-01T09:00:00Z", field="department_id", previous="1", new="2"),
            _change(ada, "2026-01-02T09:00:00Z", field="department_id", previous="99", new="2"),
            _change(ada, "2026-01-03T09:00:00Z", field="department_id", previous="1", new="98"),
            _change(ada, "2026-01-04T09:00:00Z", field="job_title", previous="1", new="2"),
        ],
    )
    items = {
        item["id"]: item
        for item in api.client.get("/changes", headers=api.headers()).json()["items"]
    }
    assert (items[1]["previous_label"], items[1]["new_label"]) == ("Engineering", "Sales")
    assert (items[1]["previous_value"], items[1]["new_value"]) == ("1", "2")
    assert (items[2]["previous_label"], items[2]["new_label"]) == (None, "Sales")
    assert (items[3]["previous_label"], items[3]["new_label"]) == ("Engineering", None)
    assert (items[4]["previous_label"], items[4]["new_label"]) == (None, None)


def test_matches_what_the_app_writes(api: Api) -> None:
    ada, bola = _two_employees(api)
    headers = api.headers()
    patched = api.client.patch(
        f"/employees/{ada}",
        headers=headers,
        json=_edit(level="M1", department_id=2),
    )
    assert patched.status_code == 200, patched.text
    ended = api.client.post(f"/employees/{bola}/status", headers=headers, json=_status())
    assert ended.status_code == 200, ended.text

    body = api.client.get("/changes", headers=headers).json()
    assert len(body["items"]) == 3
    by_field = {item["field"]: item for item in body["items"]}
    assert set(by_field) == {"level", "department_id", "status"}

    level = by_field["level"]
    assert level["employee_id"] == ada
    assert (level["previous_value"], level["new_value"]) == ("IC3", "M1")
    assert (level["previous_label"], level["new_label"]) == (None, None)
    assert level["reason"] == "Promotion"
    assert level["effective_date"] == "2026-05-01"
    assert level["changed_by"] == "hr@acme.test"
    assert level["employee_name"] == "Ada Okoye"
    assert level["department"] == {"id": 2, "name": "Sales"}

    moved = by_field["department_id"]
    assert (moved["previous_value"], moved["new_value"]) == ("1", "2")
    assert (moved["previous_label"], moved["new_label"]) == ("Engineering", "Sales")

    status = by_field["status"]
    assert status["employee_id"] == bola
    assert (status["previous_value"], status["new_value"]) == ("active", "terminated")
    assert status["effective_date"] == "2026-06-30"

    per_employee = api.client.get(f"/employees/{ada}/changes", headers=headers).json()["items"]
    assert {item["id"] for item in per_employee} == {level["id"], moved["id"]}
    ids = [item["id"] for item in body["items"]]
    assert ids == sorted(ids, reverse=True)
    only_status = api.client.get("/changes", params={"field": "status"}, headers=headers)
    assert [item["id"] for item in only_status.json()["items"]] == [status["id"]]


def test_requires_token(api: Api) -> None:
    assert api.client.get("/changes").status_code == 401
    assert api.client.get("/changes", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_revoked_token_is_401(api: Api) -> None:
    login = api.client.post(
        "/auth/login",
        json={"email": api.settings.hr_email, "password": api.settings.hr_password},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert api.client.get("/changes", headers=headers).status_code == 200
    assert api.client.post("/auth/logout", headers=headers).status_code == 204
    assert api.client.get("/changes", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {"since": "2026-13-01"},
        {"since": "yesterday"},
        {"until": "2026-02-30"},
        {"until": "20260101"},
        {"since": "2026-03-01", "until": "2026-01-01"},
        {"field": "salary"},
        {"field": "Level"},
        {"field": "base_salary_scaled"},
        {"limit": "0"},
        {"limit": "101"},
        {"department_id": "x"},
        {"cursor": "garbage"},
        {"employee_id": "x" * 65},
        {"field": "x" * 33},
        {"since": "2" * 41},
        {"until": "2" * 41},
        {"changed_by": "x" * 255},
        {"cursor": "x" * 513},
    ],
)
def test_invalid_input_is_422(api: Api, params: dict[str, str]) -> None:
    response = api.client.get("/changes", params=params, headers=api.headers())
    assert response.status_code == 422


def test_max_length_values_are_accepted(api: Api) -> None:
    params = {"employee_id": "x" * 64, "changed_by": "x" * 254}
    response = api.client.get("/changes", params=params, headers=api.headers())
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_foreign_cursors_are_422(api: Api) -> None:
    secret = api.settings.app_secret
    headers = api.headers()
    directory_like = sign_cursor(
        secret,
        {"sort": "name", "direction": "asc", "values": ["a", "b"], "id": "x", "side": "next"},
    )
    audit_like = sign_cursor(secret, {"kind": "audit", "created_at": "z", "id": 1})
    wrong_types = sign_cursor(secret, {"kind": "changes", "created_at": 5, "id": "x"})
    bool_id = sign_cursor(secret, {"kind": "changes", "created_at": "z", "id": True})
    other_secret = sign_cursor("other-secret", {"kind": "changes", "created_at": "z", "id": 1})
    for token in (directory_like, audit_like, wrong_types, bool_id, other_secret):
        response = api.client.get("/changes", params={"cursor": token}, headers=headers)
        assert response.status_code == 422


def test_real_directory_cursor_is_422(api: Api) -> None:
    _create(api)
    _create(api, email="grace@acme.test", first_name="Grace")
    headers = api.headers()
    directory = api.client.get("/employees", params={"limit": 1}, headers=headers).json()
    assert directory["next_cursor"]
    response = api.client.get(
        "/changes", params={"cursor": directory["next_cursor"]}, headers=headers
    )
    assert response.status_code == 422


def test_real_audit_cursor_is_422(api: Api) -> None:
    ada = str(_create(api)["id"])
    headers = api.headers()
    for version in (1, 2):
        raised = api.client.patch(
            f"/employees/{ada}/compensation",
            headers=headers,
            json={
                "base_salary_scaled": str(15500000 + version * 100),
                "variable_pay_scaled": "0",
                "reason": "Raise",
                "effective_date": "2026-05-01",
                "version_id": version,
            },
        )
        assert raised.status_code == 200, raised.text
    page = api.client.get("/audit", params={"limit": 1}, headers=headers).json()
    assert page["next_cursor"]
    response = api.client.get("/changes", params={"cursor": page["next_cursor"]}, headers=headers)
    assert response.status_code == 422


def test_read_only(api: Api) -> None:
    ada, _ = _two_employees(api)
    _insert(api.db_path, [_change(ada, "2026-01-01T09:00:00Z")])
    headers = api.headers()

    def snapshot() -> tuple[object, ...]:
        connection = sqlite3.connect(api.db_path)
        try:
            return (
                connection.execute("SELECT * FROM employee_change_logs").fetchall(),
                connection.execute("SELECT * FROM employees ORDER BY id").fetchall(),
                connection.total_changes,
            )
        finally:
            connection.close()

    before = snapshot()
    api.client.get("/changes", headers=headers)
    api.client.get("/changes", params={"employee_id": ada, "field": "level"}, headers=headers)
    assert snapshot() == before
    for method in ("post", "put", "patch", "delete"):
        assert getattr(api.client, method)("/changes", headers=headers).status_code == 405
    assert snapshot() == before
