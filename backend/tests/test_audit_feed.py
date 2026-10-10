# ruff: noqa: F401, F811
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_directory import _auth, _employee, _seed, api

from app.directory import sign_cursor
from app.settings import Settings

Api = tuple[TestClient, Settings, Path]

_AUDIT_SQL = """
INSERT INTO compensation_audit_logs (
  employee_id, previous_base_salary_scaled, new_base_salary_scaled,
  previous_variable_pay_scaled, new_variable_pay_scaled, currency_code,
  fx_units_per_usd_scaled, previous_salary_usd_scaled, new_salary_usd_scaled,
  reason, effective_date, changed_by, created_at
) VALUES (?, '100', '200', '0', '0', 'USD', '1000000', '100', '200', ?, ?, ?, ?)
"""


def _audit(
    employee_id: str,
    created_at: str,
    *,
    effective_date: str = "2026-01-01",
    changed_by: str = "hr@acme.test",
    reason: str = "Review",
) -> tuple[str, str, str, str, str]:
    return (employee_id, reason, effective_date, changed_by, created_at)


def _insert(db_path: Path, rows: list[tuple[str, str, str, str, str]]) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.executemany(_AUDIT_SQL, rows)
        connection.commit()
    finally:
        connection.close()


def _employees() -> list[dict[str, object]]:
    return [
        _employee(id="e1", employee_number="EMP-1", email="e1@acme.test"),
        _employee(
            id="e2",
            employee_number="EMP-2",
            email="e2@acme.test",
            first_name="Bola",
            last_name="Ade",
            department_id=2,
            department_name="Sales",
        ),
    ]


def _walk(client: TestClient, headers: dict[str, str], **params: object) -> list[int]:
    ids: list[int] = []
    cursor = None
    while True:
        page_params = {**params, "cursor": cursor} if cursor else params
        response = client.get("/audit", params=page_params, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == {"items", "next_cursor"}
        ids.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return ids


def test_newest_first_with_employee_context(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _employees())
    _insert(
        db_path,
        [
            _audit("e1", "2026-01-01T09:00:00Z"),
            _audit("e2", "2026-03-01T09:00:00Z"),
            _audit("e1", "2026-02-01T09:00:00Z"),
        ],
    )
    body = client.get("/audit", headers=_auth(settings)).json()
    assert [item["id"] for item in body["items"]] == [2, 3, 1]
    assert body["next_cursor"] is None
    first = body["items"][0]
    assert first["employee_id"] == "e2"
    assert first["employee_number"] == "EMP-2"
    assert first["employee_name"] == "Bola Ade"
    assert first["department"] == {"id": 2, "name": "Sales"}
    assert first["salary_scale"] == 2
    assert first["fx_scale"] == 6
    assert first["salary_usd_scale"] == 2
    assert first["previous_base_salary_scaled"] == "100"
    assert first["new_salary_usd_scaled"] == "200"
    assert first["changed_by"] == "hr@acme.test"
    assert not any(isinstance(value, float) for value in first.values())


def test_pagination_with_shared_timestamps(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _employees())
    stamps = ["2026-01-01T09:00:00Z", "2026-01-02T09:00:00Z", "2026-01-02T09:00:00Z"]
    rows = [_audit("e1" if i % 2 else "e2", stamps[i % 3]) for i in range(37)]
    _insert(db_path, rows)
    headers = _auth(settings)
    everything = client.get("/audit", params={"limit": 100}, headers=headers).json()
    unpaged = [item["id"] for item in everything["items"]]
    assert len(unpaged) == 37
    for limit in (1, 2, 5, 36, 37):
        walked = _walk(client, headers, limit=limit)
        assert walked == unpaged
        assert len(set(walked)) == 37


def test_filters(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _employees())
    _insert(
        db_path,
        [
            _audit("e1", "2026-01-01T09:00:00Z", effective_date="2026-01-10"),
            _audit("e2", "2026-01-02T09:00:00Z", effective_date="2026-02-10", changed_by="x@a"),
            _audit("e1", "2026-01-03T09:00:00Z", effective_date="2026-03-10", changed_by="x@a"),
        ],
    )
    headers = _auth(settings)

    def ids(**params: object) -> list[int]:
        response = client.get("/audit", params=params, headers=headers)
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert ids(employee_id="e1") == [3, 1]
    assert ids(employee_id="missing") == []
    assert ids(department_id=2) == [2]
    assert ids(since="2026-02-10") == [3, 2]
    assert ids(until="2026-02-10") == [2, 1]
    assert ids(since="2026-02-01", until="2026-02-28") == [2]
    assert ids(changed_by="x@a") == [3, 2]
    assert ids(changed_by="x@a", employee_id="e1", since="2026-03-10") == [3]
    assert _walk(client, headers, changed_by="x@a", limit=1) == [3, 2]


def test_requires_token(api: Api) -> None:
    client, _, _ = api
    assert client.get("/audit").status_code == 401
    assert client.get("/audit", headers={"Authorization": "Bearer nope"}).status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {"since": "2026-13-01"},
        {"since": "yesterday"},
        {"until": "2026-02-30"},
        {"until": "20260101"},
        {"since": "2026-03-01", "until": "2026-01-01"},
        {"limit": "0"},
        {"limit": "101"},
        {"department_id": "x"},
        {"cursor": "garbage"},
    ],
)
def test_invalid_input_is_422(api: Api, params: dict[str, str]) -> None:
    client, settings, _ = api
    response = client.get("/audit", params=params, headers=_auth(settings))
    assert response.status_code == 422


def test_foreign_cursors_are_422(api: Api) -> None:
    client, settings, _ = api
    headers = _auth(settings)
    directory_like = sign_cursor(
        settings.app_secret,
        {"sort": "name", "direction": "asc", "values": ["a", "b"], "id": "x", "side": "next"},
    )
    wrong_types = sign_cursor(
        settings.app_secret, {"kind": "audit", "created_at": 5, "id": "x"}
    )
    for token in (directory_like, wrong_types):
        assert client.get("/audit", params={"cursor": token}, headers=headers).status_code == 422
    other = sign_cursor("other-secret", {"kind": "audit", "created_at": "z", "id": 1})
    assert client.get("/audit", params={"cursor": other}, headers=headers).status_code == 422


def test_read_only(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _employees())
    _insert(db_path, [_audit("e1", "2026-01-01T09:00:00Z")])
    headers = _auth(settings)

    def snapshot() -> tuple[object, ...]:
        connection = sqlite3.connect(db_path)
        try:
            return (
                connection.execute("SELECT * FROM compensation_audit_logs").fetchall(),
                connection.execute("SELECT * FROM employees ORDER BY id").fetchall(),
                connection.total_changes,
            )
        finally:
            connection.close()

    before = snapshot()
    client.get("/audit", headers=headers)
    client.get("/audit", params={"employee_id": "e1", "since": "2026-01-01"}, headers=headers)
    assert snapshot() == before
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/audit", headers=headers)
        assert response.status_code == 405
    assert snapshot() == before
