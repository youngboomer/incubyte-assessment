"""Time the real CompPulse paths on a fresh database.

The script seeds with ``app.seed.apply_seed``, then drives the FastAPI
routes through ``TestClient``. SQLAlchemy's SQLite dialect renders
``OFFSET 0`` beside every LIMIT. A zero offset does not skip rows, so the
script fails only when the offset parameter is non-zero. It does not claim
these paths are O(1).
"""

from __future__ import annotations

import argparse
import asyncio
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

    def timed(name: str, complexity: str, call):
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
        print(
            f"{name} seconds={elapsed:.4f} {offset} complexity={complexity} "
            f"statements={len(captured)}"
        )
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
            "O(limit)-after-index-seek",
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
            last = timed(
                name,
                "O(limit)-after-index-seek-not-O(1)",
                lambda query=query: page(query),
            )
            cursor = last["next_cursor"]
        print(
            f"deep_page_reached pages={args.deep_pages} items={len(last['items'])} "
            f"has_next={last['next_cursor'] is not None}"
        )

        found = timed(
            "search_page",
            "FTS-prefix-not-O(1)",
            lambda: page("q=kabir&limit=20"),
        )
        print(f"search_total={found['total']}")
        employee_id = found["items"][0]["id"]

        def one():
            response = client.get(f"/employees/{employee_id}", headers=headers)
            assert response.status_code == 200, response.text
            return response.json()

        employee = timed("id_lookup", "O(1)-primary-key", one)

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

        stats = timed("analytics", "O(n)-active-rows-not-O(1)", overview)
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

        updated = timed("pay_update", "O(1)-point-update-plus-audit-insert", pay)
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

        conflict = timed("stale_version", "O(1)-rejected-write", stale)
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

        timed("fx_recompute", "O(employees-on-currency)-not-O(1)", fx)

    print("load_ok")


if __name__ == "__main__":
    main()
