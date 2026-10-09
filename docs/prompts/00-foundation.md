# Foundation

## Summary
Boot FastAPI, the SQLite schema, the money module, and a Next.js shell that can reach `/health` on the private network.

## Owns
- `backend/` app factory, settings, async engine, PRAGMAs, models, schema initializer, `app/money.py` and its tests
- Empty routers registered in one list: health, auth, employees, analytics, fx
- `GET /health` only. Other routers return 404 until their PR
- `web/` Next.js shell that server-fetches `BACKEND_URL/health`
- `compose.yaml`, `compose.dev.yaml`, Dockerfiles, GitHub Actions (ruff, pytest, `tsc`)

## Rules
- Follow `docs/architecture.md` and `docs/api-contract.md`
- Async SQLAlchemy, `sqlite+aiosqlite`, `NullPool`, one schema initializer for FTS5 and triggers
- Money tests: `"12000050"` at scale 2 is `Decimal("120000.50")`; JPY scale 0; reject `"12.00"` and `"1e5"`; half-even back to digits
- Do not publish backend port 8000
- Do not add CORS, Faker, Postgres, or a float money column

## Done when
- `GET /health` returns `{"status":"ok"}` through `TestClient`
- `pytest` and `tsc --noEmit` pass
- `compose.dev.yaml` serves the shell on host port 3000 and the backend has no host port
