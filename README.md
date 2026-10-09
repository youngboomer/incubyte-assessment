# CompPulse

Salary management for ACME’s HR manager. The directory is seeded with 10,000 employees and designed to keep working at 100,000.

## Summary
- FastAPI and async SQLAlchemy, SQLite, Next.js
- nginx-proxy-manager is an existing host service and proxies to the frontend
- The backend listens on the internal Docker network

## Docs
- `docs/prd.md` — goal, scope, exclusions
- `docs/architecture.md` — schema, money, search, concurrency, network
- `docs/api-contract.md` — request and response shapes
- `docs/performance.md` — measured cost of the 100,000-row paths
- `docs/verification-report.md` and `docs/verification-report.html` — second pass and test evidence
- `docs/ai-usage.md` — how the agents and local checks were used
- `docs/prompts/` — PR specs for the build

## Demo login
- Email: `hr@acme.test`
- Password: `compulse-demo`

The password is a demo default from `.env.example`. Change `APP_SECRET` and `HR_PASSWORD` before a public host.

## Run
- `docker compose up --build` publishes the frontend on `127.0.0.1:65525`. The backend listens on 65524 inside the Docker network and has no host port.
- The frontend is on `edge` and `internal`. The backend is only on `internal`. Docker does not publish a port from an internal-only container.
- Compose does not start nginx-proxy-manager.

Proxy host, in the nginx-proxy-manager service that is already running:

- Forward hostname `127.0.0.1`, port `65525`, scheme `http`
- Websockets on
- No forward to port 65524

## Demo video

About three minutes. Record against the running frontend.

1. Open the site and log in as `hr@acme.test` / `compulse-demo`.
2. Search the directory, filter to one country, and open a person. Say that local pay is the stored base and variable amounts, and USD is local pay divided by the planning rate at the time it was saved.
3. Change the salary with a reason and an effective date. Show the new audit row: local pay, USD, and the planning rate from that change.
4. Submit the form again without reloading. The page says `Record was modified. Reload and try again.` and does not write a second audit row.
5. Open the dashboard. Read headcount, total, average, the inclusive quartiles, and one histogram bucket. Those figures are the active employees only.

## Commits and pull requests
One summary line, then bullets.

```text
## Summary
<one sentence>

## Changes
- <what landed>
```
