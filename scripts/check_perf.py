"""Time the real CompPulse paths on a fresh database.

The script seeds with ``app.seed.apply_seed``, then drives the FastAPI
routes through ``TestClient``. SQLAlchemy's SQLite dialect renders
``OFFSET 0`` beside every LIMIT. A zero offset does not skip rows, so the
script fails only when the offset parameter is non-zero. Complexity labels
for directory pages come from ``EXPLAIN QUERY PLAN`` of the statements that
request ran. The script does not claim these paths are O(1).
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.db import create_db_engine, init_schema
from app.main import create_app
from app.seed import apply_seed
from app.settings import Settings


def _url(path: Path) -> str:
    return "sqlite+aiosqlite:///" + path.resolve().as_posix()


def _skips_rows(statement: str, parameters: object) -> bool:
    """SQLite's SQLAlchemy dialect always renders ``OFFSET 0`` beside LIMIT.

    A zero offset does not skip rows. A positive offset would.
    """
    if "OFFSET" not in statement.upper():
        return False
    # A literal ``OFFSET 0`` has no bound offset parameter.
    tail = statement.upper().rsplit("OFFSET", 1)[1]
    if tail.strip() == "0":
        return False
    values = _last_param_set(parameters)
    if not values:
        return True
    return values[-1] not in (0, None)


def _last_param_set(parameters: object) -> list[object]:
    if isinstance(parameters, dict):
        return list(parameters.values())
    if isinstance(parameters, (tuple, list)):
        if parameters and all(isinstance(item, (tuple, list, dict)) for item in parameters):
            last = parameters[-1]
            if isinstance(last, dict):
                return list(last.values())
            return list(last)
        return list(parameters)
    return []


def _seed(database_url: str, count: int) -> float:
    engine = create_db_engine(database_url)

    async def _run() -> None:
        await init_schema(engine)
        await apply_seed(engine, count, reset=True)
        await engine.dispose()

    started = time.perf_counter()
    asyncio.run(_run())
    return time.perf_counter() - started


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--deep-pages", type=int, default=40)
    args = parser.parse_args()
    if args.count < 1 or args.deep_pages < 1:
        raise SystemExit("count and deep-pages must be positive")

    database_url = _url(args.database)
    seed_seconds = _seed(database_url, args.count)
    print(f"seed count={args.count} seconds={seed_seconds:.4f} complexity=O(n)")

    settings = Settings(
        database_url=database_url,
        seed_count=0,
        app_secret="perf-secret",
        hr_email="hr@acme.test",
        hr_password="compulse-demo",
    )
    app = create_app(settings)
    captured: list[tuple[str, object]] = []

    def _capture(_conn, _cursor, statement, parameters, _context, _executemany) -> None:
        captured.append((statement, parameters))

    event.listen(app.state.engine.sync_engine, "before_cursor_execute", _capture)

    def _bound(parameters: object) -> object:
        if isinstance(parameters, dict):
            return parameters
        if isinstance(parameters, (tuple, list)):
            if parameters and all(isinstance(item, (tuple, list, dict)) for item in parameters):
                return parameters[0]
            return parameters
        return ()

    def _plans(rows: list[tuple[str, object]]) -> list[str]:
        described: list[str] = []
        connection = sqlite3.connect(args.database)
        try:
            for statement, parameters in rows:
                kind = statement.lstrip().upper()
                if not kind.startswith(("SELECT", "UPDATE", "INSERT", "DELETE")):
                    continue
                bound = _bound(parameters)
                plan_rows = connection.execute("EXPLAIN QUERY PLAN " + statement, bound).fetchall()
                plan = " ; ".join(str(row[-1]) for row in plan_rows)
                opcodes = [
                    str(row[1]) for row in connection.execute("EXPLAIN " + statement, bound)
                ]
                counts = ",".join(
                    f"{name}:{opcodes.count(name)}"
                    for name in ("Rewind", "SeekGE", "SeekLE", "SeekGT", "SeekLT")
                )
                described.append(f"{plan} opcodes={counts}")
        finally:
            connection.close()
        return described

    def _complexity(name: str, plans: list[str]) -> str:
        joined = " | ".join(plans)
        if name in {
            "filtered_page",
            "keyset_step",
            "deep_keyset_page",
            "salary_first_page",
            "salary_seek_step",
            "salary_seek_page",
        }:
            if "idx_emp_status_country" in joined and "USE TEMP B-TREE FOR ORDER BY" in joined:
                return "filter-index-scan-plus-sort-not-salary-seek-not-O(1)"
            if "SEARCH employees USING INDEX idx_emp_salary_usd (<expr>" in joined:
                return "O(limit)-after-salary-index-seek-not-O(1)"
            if "SEARCH employees USING INDEX idx_emp_base_salary (<expr>" in joined:
                return "O(limit)-after-base-salary-index-seek-not-O(1)"
            if "SCAN employees USING INDEX idx_emp_salary_usd" in joined:
                return "O(limit)-ordered-salary-index-scan-not-O(1)"
            return "unlabeled"
        if name == "search_page":
            if "employees_fts" in joined:
                return "FTS-prefix-not-O(1)"
            return "unlabeled"
        if name == "id_lookup":
            return "O(1)-primary-key"
        if name == "analytics":
            return "O(n)-active-rows-not-O(1)"
        if name == "pay_update":
            return "O(1)-point-update-plus-audit-insert"
        if name == "stale_version":
            return "O(1)-rejected-write"
        if name == "fx_recompute":
            return "O(employees-on-currency)-not-O(1)"
        return "unlabeled"

    def timed(name: str, call):
        captured.clear()
        started = time.perf_counter()
        result = call()
        elapsed = time.perf_counter() - started
        saw_zero_offset = False
        for statement, parameters in captured:
            if _skips_rows(statement, parameters):
                raise SystemExit(f"{name} skipped rows with a non-zero OFFSET")
            if "OFFSET" in statement.upper():
                saw_zero_offset = True
        offset = (
            "offset_param=0 row_skip=no" if saw_zero_offset else "offset_param=absent row_skip=no"
        )
        plans = _plans(captured)
        complexity = _complexity(name, plans)
        print(
            f"{name} seconds={elapsed:.4f} {offset} complexity={complexity} "
            f"statements={len(captured)}"
        )
        for index, plan in enumerate(plans):
            print(f"{name} plan[{index}]={plan}")
        return result

    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"email": settings.hr_email, "password": settings.hr_password},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        def page(query: str):
            response = client.get(f"/employees?{query}", headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
            for item in body["items"]:
                for key, value in item.items():
                    if isinstance(value, float):
                        raise SystemExit(f"float field {key}")
            return body

        first = timed(
            "filtered_page",
            lambda: page("country=IN&status=active&sort=salary_usd&direction=asc&limit=50"),
        )
        print(f"filtered_page total={first['total']} items={len(first['items'])}")

        cursor = first["next_cursor"]
        last = first
        for index in range(args.deep_pages):
            if not cursor:
                raise SystemExit(f"ran out of cursors at page {index}")
            query = (
                "country=IN&status=active&sort=salary_usd&direction=asc&limit=50"
                f"&cursor={cursor}"
            )
            name = "deep_keyset_page" if index == args.deep_pages - 1 else "keyset_step"
            last = timed(name, lambda query=query: page(query))
            cursor = last["next_cursor"]
        print(
            f"deep_page_reached pages={args.deep_pages} items={len(last['items'])} "
            f"has_next={last['next_cursor'] is not None}"
        )

        salary_first = timed(
            "salary_first_page",
            lambda: page("sort=salary_usd&direction=asc&limit=50"),
        )
        salary_cursor = salary_first["next_cursor"]
        salary_last = salary_first
        for index in range(args.deep_pages):
            if not salary_cursor:
                raise SystemExit(f"ran out of salary cursors at page {index}")
            query = f"sort=salary_usd&direction=asc&limit=50&cursor={salary_cursor}"
            name = "salary_seek_page" if index == args.deep_pages - 1 else "salary_seek_step"
            salary_last = timed(name, lambda query=query: page(query))
            salary_cursor = salary_last["next_cursor"]
        print(
            f"salary_seek_reached pages={args.deep_pages} items={len(salary_last['items'])} "
            f"has_next={salary_last['next_cursor'] is not None}"
        )

        search_term = page("limit=1")["items"][0]["first_name"]
        found = timed(
            "search_page",
            lambda: page(f"q={search_term}&limit=20"),
        )
        print(f"search_total={found['total']}")
        employee_id = found["items"][0]["id"]

        def one():
            response = client.get(f"/employees/{employee_id}", headers=headers)
            assert response.status_code == 200, response.text
            return response.json()

        employee = timed("id_lookup", one)

        def overview():
            response = client.get("/analytics/overview", headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
            if isinstance(body["headcount"], float):
                raise SystemExit("headcount was a float")
            for key in (
                "total_salary_usd_scaled",
                "average_salary_usd_scaled",
                "p25_salary_usd_scaled",
                "p50_salary_usd_scaled",
                "p75_salary_usd_scaled",
            ):
                if not isinstance(body[key], str) or not body[key].lstrip("-").isdigit():
                    raise SystemExit(f"{key} is not a digit string: {body[key]!r}")
            return body

        stats = timed("analytics", overview)
        print(f"analytics_headcount={stats['headcount']} histogram={len(stats['histogram'])}")

        def pay():
            response = client.patch(
                f"/employees/{employee_id}/compensation",
                headers=headers,
                json={
                    "base_salary_scaled": employee["base_salary_scaled"],
                    "variable_pay_scaled": employee["variable_pay_scaled"],
                    "reason": "Perf probe",
                    "effective_date": "2026-04-01",
                    "version_id": employee["version_id"],
                },
            )
            assert response.status_code == 200, response.text
            return response.json()

        updated = timed("pay_update", pay)
        print(f"pay_version={updated['version_id']}")

        def stale():
            response = client.patch(
                f"/employees/{employee_id}/compensation",
                headers=headers,
                json={
                    "base_salary_scaled": employee["base_salary_scaled"],
                    "variable_pay_scaled": employee["variable_pay_scaled"],
                    "reason": "Stale probe",
                    "effective_date": "2026-04-02",
                    "version_id": employee["version_id"],
                },
            )
            return response

        conflict = timed("stale_version", stale)
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["detail"] == "Record was modified. Reload and try again."
        audit = client.get(f"/employees/{employee_id}/audit", headers=headers)
        assert audit.status_code == 200, audit.text
        reasons = [item["reason"] for item in audit.json()["items"]]
        if reasons.count("Stale probe") != 0:
            raise SystemExit("stale write inserted an audit row")
        print(f"stale_status=409 audit_rows={len(reasons)}")

        def fx():
            response = client.patch(
                "/fx/JPY",
                headers=headers,
                json={"units_per_usd_scaled": "149000000"},
            )
            assert response.status_code == 200, response.text
            return response.json()

        timed("fx_recompute", fx)

    print("load_ok")


if __name__ == "__main__":
    main()
