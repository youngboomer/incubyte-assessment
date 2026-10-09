import csv
import io
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.deps import issue_token
from app.main import create_app
from app.search import sanitize_fts_query
from app.settings import Settings

_NOW = "2026-01-01T00:00:00Z"
_LEVELS = ["IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"]
_STATUSES = ["active", "terminated"]
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


def _employee(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "emp-1",
        "employee_number": "EMP-00001",
        "first_name": "Ada",
        "last_name": "Okoye",
        "email": "ada.okoye@acme.test",
        "job_title": "Software Engineer",
        "department_id": 1,
        "department_name": "Engineering",
        "country_code": "US",
        "country_name": "United States",
        "currency_code": "USD",
        "currency_name": "US Dollar",
        "minor_scale": 2,
        "units_per_usd_scaled": "1000000",
        "level": "IC3",
        "base_salary_scaled": "15500000",
        "variable_pay_scaled": "0",
        "salary_usd_scaled": "15500000",
        "status": "active",
        "hire_date": "2021-03-15",
        "comp_effective_date": "2025-04-01",
        "version_id": 1,
    }
    row.update(overrides)
    return row


def _seed(db_path: Path, employees: list[dict[str, object]]) -> None:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        currencies: dict[object, tuple[object, ...]] = {}
        countries: dict[object, tuple[object, ...]] = {}
        departments: dict[object, tuple[object, ...]] = {}
        for row in employees:
            currencies[row["currency_code"]] = (
                row["currency_code"],
                row["currency_name"],
                row["minor_scale"],
                row["units_per_usd_scaled"],
            )
            countries[row["country_code"]] = (
                row["country_code"],
                row["country_name"],
                row["currency_code"],
            )
            departments[row["department_id"]] = (row["department_id"], row["department_name"])
        connection.executemany(
            "INSERT INTO currencies (code, name, minor_scale, units_per_usd_scaled, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [(*values, _NOW) for values in currencies.values()],
        )
        connection.executemany(
            "INSERT INTO countries (code, name, currency_code) VALUES (?, ?, ?)",
            list(countries.values()),
        )
        connection.executemany(
            "INSERT INTO departments (id, name) VALUES (?, ?)",
            list(departments.values()),
        )
        connection.executemany(
            _EMPLOYEE_SQL,
            [
                (
                    row["id"],
                    row["employee_number"],
                    row["first_name"],
                    row["last_name"],
                    row["email"],
                    row["job_title"],
                    row["department_id"],
                    row["country_code"],
                    row["currency_code"],
                    row["level"],
                    row["base_salary_scaled"],
                    row["variable_pay_scaled"],
                    row["salary_usd_scaled"],
                    row["status"],
                    row["hire_date"],
                    row["comp_effective_date"],
                    row["version_id"],
                    _NOW,
                    _NOW,
                )
                for row in employees
            ],
        )
        connection.commit()
    finally:
        connection.close()


@pytest.fixture
def api(tmp_path: Path) -> tuple[TestClient, Settings, Path]:
    db_path = tmp_path / "directory.db"
    settings = Settings(
        database_url=_sqlite_url(db_path),
        app_secret="test-secret",
        hr_email="hr@acme.test",
        seed_count=0,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, settings, db_path


def _auth(settings: Settings, email: str | None = None) -> dict[str, str]:
    token = issue_token(settings.app_secret, settings.hr_email if email is None else email)
    return {"Authorization": f"Bearer {token}"}


def _assert_no_float(value: object) -> None:
    if isinstance(value, float):
        raise AssertionError(value)
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_float(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_float(item)


def _assert_employee(payload: dict[str, object], row: dict[str, object]) -> None:
    assert set(payload) == {
        "id",
        "employee_number",
        "first_name",
        "last_name",
        "email",
        "job_title",
        "department",
        "country",
        "currency_code",
        "level",
        "base_salary_scaled",
        "variable_pay_scaled",
        "salary_scale",
        "salary_usd_scaled",
        "salary_usd_scale",
        "status",
        "hire_date",
        "comp_effective_date",
        "version_id",
    }
    assert payload["id"] == row["id"]
    assert payload["employee_number"] == row["employee_number"]
    assert payload["first_name"] == row["first_name"]
    assert payload["last_name"] == row["last_name"]
    assert payload["email"] == row["email"]
    assert payload["job_title"] == row["job_title"]
    assert payload["department"] == {"id": row["department_id"], "name": row["department_name"]}
    assert payload["country"] == {"code": row["country_code"], "name": row["country_name"]}
    assert payload["currency_code"] == row["currency_code"]
    assert payload["level"] == row["level"]
    assert payload["base_salary_scaled"] == row["base_salary_scaled"]
    assert payload["variable_pay_scaled"] == row["variable_pay_scaled"]
    assert payload["salary_scale"] == row["minor_scale"]
    assert type(payload["salary_scale"]) is int
    assert payload["salary_usd_scaled"] == row["salary_usd_scaled"]
    assert payload["salary_usd_scale"] == 2
    assert type(payload["salary_usd_scale"]) is int
    assert payload["status"] == row["status"]
    assert payload["hire_date"] == row["hire_date"]
    assert payload["comp_effective_date"] == row["comp_effective_date"]
    assert payload["version_id"] == row["version_id"]
    assert type(payload["version_id"]) is int
    _assert_no_float(payload)


def _ids(client: TestClient, headers: dict[str, str], **params: object) -> list[str]:
    response = client.get("/employees", params=params, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"items", "next_cursor", "prev_cursor", "total"}
    return [item["id"] for item in body["items"]]


def test_sanitize_fts_query() -> None:
    assert sanitize_fts_query("Ada Okoye") == "Ada* AND Okoye*"
    assert sanitize_fts_query("  ada   okoye ") == "ada* AND okoye*"
    assert sanitize_fts_query("   ") is None
    assert sanitize_fts_query('say "hello": world') == "say* AND hello* AND world*"
    assert sanitize_fts_query('"*:(^)"') is None
    assert sanitize_fts_query("a*b") == "ab*"
    assert sanitize_fts_query("(hello)") == "hello*"
    assert sanitize_fts_query("x^y") == "xy*"
    assert sanitize_fts_query('"foo:bar"') == "foobar*"
    assert sanitize_fts_query("Mary-Jane") == "Mary* AND Jane*"


def test_page_size_and_keyset(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    rows = [
        _employee(
            id=f"emp-{index:03d}",
            employee_number=f"EMP-{index:05d}",
            first_name="Ada",
            last_name=f"{index:03d}",
            email=f"ada.{index}@acme.test",
        )
        for index in range(51)
    ]
    _seed(db_path, rows)
    expected = [row["id"] for row in rows]

    first = client.get("/employees", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["total"] == 51
    assert type(body["total"]) is int
    assert len(body["items"]) == 50
    assert body["prev_cursor"] is None
    assert isinstance(body["next_cursor"], str)
    assert [item["id"] for item in body["items"]] == expected[:50]

    second = client.get("/employees", params={"cursor": body["next_cursor"]}, headers=headers)
    assert second.status_code == 200
    page = second.json()
    assert page["total"] == 51
    assert [item["id"] for item in page["items"]] == expected[50:]
    assert page["next_cursor"] is None
    assert isinstance(page["prev_cursor"], str)

    back = client.get("/employees", params={"cursor": page["prev_cursor"]}, headers=headers)
    assert back.status_code == 200
    assert [item["id"] for item in back.json()["items"]] == expected[:50]
    assert back.json()["prev_cursor"] is None

    seen: list[str] = []
    cursor = None
    previous = None
    for _ in range(40):
        params: dict[str, object] = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/employees", params=params, headers=headers)
        assert response.status_code == 200, response.text
        chunk = response.json()
        assert chunk["total"] == 51
        assert 1 <= len(chunk["items"]) <= 2
        if previous is None:
            assert chunk["prev_cursor"] is None
        else:
            assert isinstance(chunk["prev_cursor"], str)
        seen.extend(item["id"] for item in chunk["items"])
        previous = chunk
        cursor = chunk["next_cursor"]
        if cursor is None:
            break
    assert seen == expected

    limited = client.get("/employees", params={"limit": 1}, headers=headers)
    assert limited.status_code == 200
    assert [item["id"] for item in limited.json()["items"]] == expected[:1]
    assert client.get("/employees", params={"limit": 0}, headers=headers).status_code == 422
    assert client.get("/employees", params={"limit": 101}, headers=headers).status_code == 422
    wide = client.get("/employees", params={"limit": 100}, headers=headers)
    assert wide.status_code == 200
    assert [item["id"] for item in wide.json()["items"]] == expected
    assert wide.json()["next_cursor"] is None


def test_combined_filters(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    match = _employee(
        id="match",
        employee_number="EMP-1",
        first_name="Ada",
        last_name="Uniquezz",
        email="match@acme.test",
        department_id=1,
        department_name="Engineering",
        country_code="US",
        country_name="United States",
        currency_code="USD",
        currency_name="US Dollar",
        status="active",
    )
    rows = [
        match,
        _employee(
            id="other-dept",
            employee_number="EMP-2",
            email="dept@acme.test",
            first_name="Ada",
            last_name="Uniquezz",
            department_id=2,
            department_name="Sales",
        ),
        _employee(
            id="other-name",
            employee_number="EMP-3",
            email="name@acme.test",
            first_name="Bob",
            last_name="Other",
        ),
        _employee(
            id="other-country",
            employee_number="EMP-4",
            email="country@acme.test",
            first_name="Ada",
            last_name="Uniquezz",
            country_code="DE",
            country_name="Germany",
            currency_code="EUR",
            currency_name="Euro",
            units_per_usd_scaled="920000",
        ),
        _employee(
            id="terminated",
            employee_number="EMP-5",
            email="terminated@acme.test",
            first_name="Ada",
            last_name="Uniquezz",
            status="terminated",
        ),
    ]
    _seed(db_path, rows)
    response = client.get(
        "/employees",
        params={
            "q": "Ada Uniquezz",
            "department_id": 1,
            "country": "US",
            "currency": "USD",
            "status": "active",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    _assert_employee(body["items"][0], match)
    assert _ids(client, headers, status="terminated") == ["terminated"]
    assert set(_ids(client, headers, q="Uniquezz")) == {
        "match",
        "other-dept",
        "other-country",
        "terminated",
    }


def test_bad_sort_and_direction(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, _db_path = api
    headers = _auth(settings)
    assert client.get("/employees", params={"sort": "salary"}, headers=headers).status_code == 422
    assert client.get("/employees", params={"sort": "rowid"}, headers=headers).status_code == 422
    assert (
        client.get("/employees", params={"direction": "sideways"}, headers=headers).status_code
        == 422
    )
    assert (
        client.get("/employees/export.csv", params={"sort": "nope"}, headers=headers).status_code
        == 422
    )


def test_bad_cursor_and_sort_mismatch(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    _seed(
        db_path,
        [
            _employee(id="emp-a", employee_number="EMP-1", email="a@acme.test", last_name="Adams"),
            _employee(id="emp-b", employee_number="EMP-2", email="b@acme.test", last_name="Baker"),
        ],
    )
    assert client.get("/employees", params={"cursor": "nope"}, headers=headers).status_code == 422
    first = client.get("/employees", params={"limit": 1, "sort": "name"}, headers=headers)
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert isinstance(cursor, str)
    tampered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
    bad = client.get("/employees", params={"cursor": tampered, "sort": "name"}, headers=headers)
    assert bad.status_code == 422
    assert bad.json()["detail"] == "Invalid cursor"

    mismatch = client.get(
        "/employees",
        params={"cursor": cursor, "sort": "salary_usd"},
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"] == "Cursor does not match sort or direction"
    flipped = client.get(
        "/employees",
        params={"cursor": cursor, "sort": "name", "direction": "desc"},
        headers=headers,
    )
    assert flipped.status_code == 422
    assert flipped.json()["detail"] == "Cursor does not match sort or direction"


def test_salary_numeric_order(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    rows = [
        _employee(
            id="b",
            employee_number="EMP-B",
            email="b@acme.test",
            base_salary_scaled="100",
            salary_usd_scaled="100",
        ),
        _employee(
            id="c",
            employee_number="EMP-C",
            email="c@acme.test",
            base_salary_scaled="500",
            salary_usd_scaled="1000",
        ),
        _employee(
            id="a",
            employee_number="EMP-A",
            email="a@acme.test",
            base_salary_scaled="900",
            salary_usd_scaled="100",
        ),
        _employee(
            id="d",
            employee_number="EMP-D",
            email="d@acme.test",
            base_salary_scaled="99",
            salary_usd_scaled="99",
        ),
    ]
    _seed(db_path, rows)
    assert _ids(client, headers, sort="salary_usd") == ["d", "a", "b", "c"]
    assert _ids(client, headers, sort="salary_usd", direction="desc") == ["c", "b", "a", "d"]

    seen: list[str] = []
    cursor = None
    for _ in range(5):
        params: dict[str, object] = {"sort": "salary_usd", "limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/employees", params=params, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == ["d", "a", "b", "c"]

    base_rows_order = _ids(client, headers, sort="base_salary")
    assert base_rows_order[0] == "d"
    assert base_rows_order[-1] == "a"
    assert _ids(client, headers, sort="salary_usd", direction="desc", limit=1) == ["c"]


def test_sort_uses_allow_listed_columns(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    _seed(
        db_path,
        [
            _employee(
                id="mmm",
                employee_number="EMP-2",
                first_name="Amy",
                last_name="Adams",
                email="amy@acme.test",
                job_title="Manager",
                department_id=1,
                department_name="Sales",
                country_code="AE",
                country_name="United Arab Emirates",
                currency_code="AED",
                currency_name="UAE Dirham",
                units_per_usd_scaled="3670000",
                hire_date="2024-01-01",
            ),
            _employee(
                id="zzz",
                employee_number="EMP-10",
                first_name="Zoe",
                last_name="Adams",
                email="zoe@acme.test",
                job_title="Engineer",
                department_id=2,
                department_name="Engineering",
                country_code="DE",
                country_name="Germany",
                currency_code="EUR",
                currency_name="Euro",
                units_per_usd_scaled="920000",
                hire_date="2020-05-01",
            ),
            _employee(
                id="aaa",
                employee_number="EMP-3",
                first_name="Ann",
                last_name="Zulu",
                email="ann@acme.test",
                job_title="Analyst",
                department_id=2,
                department_name="Engineering",
                country_code="US",
                country_name="United States",
                hire_date="2022-02-02",
            ),
        ],
    )
    assert _ids(client, headers, sort="name") == ["mmm", "zzz", "aaa"]
    assert _ids(client, headers, sort="department") == ["aaa", "zzz", "mmm"]
    assert _ids(client, headers, sort="country") == ["zzz", "mmm", "aaa"]
    assert _ids(client, headers, sort="title") == ["aaa", "zzz", "mmm"]
    assert _ids(client, headers, sort="employee_number") == ["zzz", "mmm", "aaa"]
    assert _ids(client, headers, sort="hire_date") == ["zzz", "aaa", "mmm"]
    assert _ids(client, headers, sort="name", direction="desc") == ["aaa", "zzz", "mmm"]


def test_missing_employee_is_404(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    row = _employee()
    _seed(db_path, [row])
    found = client.get("/employees/emp-1", headers=headers)
    assert found.status_code == 200
    _assert_employee(found.json(), row)
    missing = client.get("/employees/missing", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Employee not found"


def test_missing_token_is_401(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, _db_path = api
    assert client.get("/employees").status_code == 401
    assert client.get("/employees").json()["detail"] == "Not authenticated"
    assert client.get("/employees/emp-1").status_code == 401
    assert client.get("/employees/export.csv").status_code == 401
    assert client.get("/reference").status_code == 401
    wrong = _auth(settings, email="other@acme.test")
    assert client.get("/employees", headers=wrong).status_code == 401
    assert client.get("/employees", headers={"Authorization": "Basic abc"}).status_code == 401


def test_query_with_quotes_and_colon_returns_200(
    api: tuple[TestClient, Settings, Path],
) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    _seed(
        db_path,
        [
            _employee(id="hit", first_name="Quotemark", email="hit@acme.test"),
            _employee(
                id="miss",
                employee_number="EMP-2",
                first_name="Other",
                last_name="Person",
                email="miss@acme.test",
            ),
        ],
    )
    quoted = client.get("/employees", params={"q": '"Quotemark:"'}, headers=headers)
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["total"] == 1
    assert quoted.json()["items"][0]["id"] == "hit"
    skipped = client.get("/employees", params={"q": '":"'}, headers=headers)
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["total"] == 2
    hyphen = client.get("/employees", params={"q": "zzzz-no-such-person"}, headers=headers)
    assert hyphen.status_code == 200, hyphen.text
    assert hyphen.json()["total"] == 0


def test_csv_major_units(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    usd = _employee(
        id="usd",
        employee_number="EMP-USD",
        first_name="Ada",
        last_name="Okoye",
        email="ada@acme.test",
        base_salary_scaled="12000050",
        variable_pay_scaled="2550",
        salary_usd_scaled="100",
        department_name="Engineering",
        country_name="United States",
        currency_code="USD",
    )
    jpy = _employee(
        id="jpy",
        employee_number="EMP-JPY",
        first_name="Kenji",
        last_name="Sato",
        email="kenji@acme.test",
        department_id=2,
        department_name="Sales",
        country_code="JP",
        country_name="Japan",
        currency_code="JPY",
        currency_name="Yen",
        minor_scale=0,
        units_per_usd_scaled="149000000",
        base_salary_scaled="8000000",
        variable_pay_scaled="149",
        salary_usd_scaled="99",
        status="active",
    )
    terminated = _employee(
        id="gone",
        employee_number="EMP-GONE",
        email="gone@acme.test",
        status="terminated",
        salary_usd_scaled="50",
    )
    _seed(db_path, [usd, jpy, terminated])

    page = client.get(
        "/employees",
        params={"sort": "salary_usd", "limit": 1, "status": "active"},
        headers=headers,
    )
    assert page.status_code == 200
    cursor = page.json()["next_cursor"]
    assert isinstance(cursor, str)

    response = client.get(
        "/employees/export.csv",
        params={"sort": "salary_usd", "status": "active", "limit": 1, "cursor": cursor},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "12000050" not in response.text
    assert "120000.50" in response.text
    reader = csv.DictReader(io.StringIO(response.text))
    exported = list(reader)
    assert reader.fieldnames == [
        "employee number",
        "name",
        "email",
        "title",
        "department",
        "country",
        "currency",
        "level",
        "base major",
        "variable major",
        "USD major",
        "status",
    ]
    assert [row["employee number"] for row in exported] == ["EMP-JPY", "EMP-USD"]
    japan, united = exported
    assert japan["name"] == "Kenji Sato"
    assert japan["department"] == "Sales"
    assert japan["country"] == "Japan"
    assert japan["currency"] == "JPY"
    assert japan["base major"] == "8000000"
    assert japan["variable major"] == "149"
    assert japan["USD major"] == "0.99"
    assert united["name"] == "Ada Okoye"
    assert united["title"] == "Software Engineer"
    assert united["department"] == "Engineering"
    assert united["country"] == "United States"
    assert united["currency"] == "USD"
    assert united["level"] == "IC3"
    assert united["base major"] == "120000.50"
    assert united["variable major"] == "25.50"
    assert united["USD major"] == "1.00"
    assert united["status"] == "active"


def test_reference(api: tuple[TestClient, Settings, Path]) -> None:
    client, settings, db_path = api
    headers = _auth(settings)
    empty = client.get("/reference", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == {
        "departments": [],
        "countries": [],
        "currencies": [],
        "levels": _LEVELS,
        "statuses": _STATUSES,
    }
    _seed(
        db_path,
        [
            _employee(
                id="us",
                department_id=2,
                department_name="Engineering",
                country_code="US",
                country_name="United States",
                currency_code="USD",
                currency_name="US Dollar",
                minor_scale=2,
                units_per_usd_scaled="1000000",
            ),
            _employee(
                id="de",
                employee_number="EMP-2",
                email="de@acme.test",
                department_id=1,
                department_name="Sales",
                country_code="DE",
                country_name="Germany",
                currency_code="EUR",
                currency_name="Euro",
                minor_scale=2,
                units_per_usd_scaled="920000",
            ),
        ],
    )
    body = client.get("/reference", headers=headers).json()
    assert body["departments"] == [
        {"id": 1, "name": "Sales"},
        {"id": 2, "name": "Engineering"},
    ]
    assert body["countries"] == [
        {"code": "DE", "name": "Germany", "currency_code": "EUR"},
        {"code": "US", "name": "United States", "currency_code": "USD"},
    ]
    assert body["currencies"] == [
        {
            "code": "EUR",
            "name": "Euro",
            "minor_scale": 2,
            "units_per_usd_scaled": "920000",
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
    assert body["levels"] == _LEVELS
    assert body["statuses"] == _STATUSES
    _assert_no_float(body)
