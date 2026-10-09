# Foundation

## Summary
Boot FastAPI, the SQLite schema, the money module, and a Next.js shell that can reach `/health` on the private network.

## Owns
- `backend/` app factory, settings, async engine, PRAGMAs, models, schema initializer, `app/money.py` and its tests
- Empty routers registered in one list: health, auth, employees, analytics, fx
- `GET /health` only. Other routers return 404 until their PR
- `web/` Next.js shell that server-fetches `BACKEND_URL/health`
- Dockerfiles and GitHub Actions (ruff, pytest, `tsc`)
- Do not edit `compose.yaml`. The orchestrator owns it.

## Rules
- Follow `docs/architecture.md` and `docs/api-contract.md`
- Async SQLAlchemy, `sqlite+aiosqlite`, `NullPool`, one schema initializer for FTS5 and triggers
- Money tests: `"12000050"` at scale 2 is `Decimal("120000.50")`; JPY scale 0; reject `"12.00"` and `"1e5"`; half-even back to digits
- Frontend listens on 65525. The host publish is `127.0.0.1:65525:65525`, already set in `compose.yaml`
- Backend listens on 65524. Do not publish that port
- `BACKEND_URL` is `http://backend:65524`
- Do not add CORS, Faker, Postgres, or a float money column

## Done when
- `GET /health` returns `{"status":"ok"}` through `TestClient`
- `pytest` and `tsc --noEmit` pass
- The frontend is hosted on port 65525 and the backend has no host port
