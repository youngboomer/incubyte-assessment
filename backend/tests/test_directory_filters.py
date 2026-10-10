# ruff: noqa: F401, F811
import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_directory import _auth, _employee, _ids, _seed, api

from app.settings import Settings

Api = tuple[TestClient, Settings, Path]


def _rows() -> list[dict[str, object]]:
    specs = [
        ("a", "IC1", "99", "active", "Alpha"),
        ("b", "IC2", "100", "active", "Bravo"),
        ("c", "IC2", "1000", "terminated", "Charlie"),
        ("d", "M1", "100", "terminated", "Delta"),
        ("e", "IC3", "5", "active", "Echo"),
    ]
    return [
        _employee(
            id=key,
            employee_number=f"EMP-{key.upper()}",
            email=f"{key}@acme.test",
            first_name=name,
            last_name="Tester",
            level=level,
            salary_usd_scaled=usd,
            base_salary_scaled=usd,
            status=status,
        )
        for key, level, usd, status, name in specs
    ]


def test_level_filter(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    headers = _auth(settings)
    assert _ids(client, headers, level="IC2", sort="employee_number") == ["b", "c"]
    assert _ids(client, headers, level="M2") == []


def test_status_filter(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    headers = _auth(settings)
    assert _ids(client, headers, status="terminated", sort="employee_number") == ["c", "d"]


def test_salary_bounds_are_numeric(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    headers = _auth(settings)
    assert _ids(client, headers, salary_usd_min="99", sort="salary_usd") == ["a", "b", "d", "c"]
    assert _ids(client, headers, salary_usd_min="100", sort="salary_usd") == ["b", "d", "c"]
    assert _ids(client, headers, salary_usd_max="99", sort="salary_usd") == ["e", "a"]
    assert _ids(client, headers, salary_usd_min="99", salary_usd_max="100", sort="salary_usd") == [
        "a",
        "b",
        "d",
    ]
    assert _ids(client, headers, salary_usd_min="0", salary_usd_max="0") == []


def test_filters_combine_with_search_and_sort(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    headers = _auth(settings)
    assert _ids(client, headers, level="IC2", salary_usd_min="100", sort="salary_usd") == [
        "b",
        "c",
    ]
    assert _ids(
        client, headers, level="IC2", status="active", salary_usd_min="100", q="Bravo"
    ) == ["b"]
    assert _ids(client, headers, q="Charlie", level="IC1") == []
    assert _ids(
        client,
        headers,
        status="terminated",
        salary_usd_max="100",
        sort="salary_usd",
        direction="desc",
    ) == ["d"]
    body = client.get(
        "/employees", params={"level": "IC2", "salary_usd_min": "100"}, headers=headers
    ).json()
    assert body["total"] == 2


def test_csv_honors_new_filters(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    response = client.get(
        "/employees/export.csv",
        params={"level": "IC2", "salary_usd_min": "100", "sort": "employee_number"},
        headers=_auth(settings),
    )
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["employee number"] for row in rows] == ["EMP-B", "EMP-C"]
    bad = client.get("/employees/export.csv", params={"level": "ZZ"}, headers=_auth(settings))
    assert bad.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"level": "IC9"},
        {"level": "ic2"},
        {"status": "retired"},
        {"salary_usd_min": "-1"},
        {"salary_usd_min": "1.5"},
        {"salary_usd_max": "abc"},
        {"salary_usd_max": ""},
        {"salary_usd_min": "9223372036854775808"},
        {"salary_usd_min": "101", "salary_usd_max": "100"},
        {"salary_usd_min": "1e3"},
    ],
)
def test_invalid_filters_are_422(api: Api, params: dict[str, str]) -> None:
    client, settings, _ = api
    response = client.get("/employees", params=params, headers=_auth(settings))
    assert response.status_code == 422


def test_int64_max_bound_is_accepted(api: Api) -> None:
    client, settings, db_path = api
    _seed(db_path, _rows())
    assert _ids(client, _auth(settings), salary_usd_max="9223372036854775807") != []


@pytest.mark.parametrize("sort", ["salary_usd", "name", "employee_number"])
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_cursor_walk_under_filters_visits_each_match_once(
    api: Api, sort: str, direction: str
) -> None:
    client, settings, db_path = api
    rows = [
        _employee(
            id=f"id-{index:03d}",
            employee_number=f"EMP-{index:03d}",
            email=f"e{index}@acme.test",
            last_name=f"L{index % 7}",
            level=("IC2", "IC3", "M1")[index % 3],
            salary_usd_scaled=str(90 + index % 25),
            base_salary_scaled=str(90 + index % 25),
        )
        for index in range(120)
    ]
    _seed(db_path, rows)
    headers = _auth(settings)
    expected = {
        row["id"]
        for row in rows
        if row["level"] == "IC2" and 95 <= int(str(row["salary_usd_scaled"])) <= 100
    }
    params: dict[str, object] = {
        "level": "IC2",
        "salary_usd_min": "95",
        "salary_usd_max": "100",
        "sort": sort,
        "direction": direction,
        "limit": 4,
    }
    seen: list[str] = []
    cursor = None
    while True:
        page_params = {**params, "cursor": cursor} if cursor else params
        page = client.get("/employees", params=page_params, headers=headers).json()
        assert page["total"] == len(expected)
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen))
    assert set(seen) == expected
