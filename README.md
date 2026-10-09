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

## Commits and pull requests
One summary line, then bullets.

```text
## Summary
<one sentence>

## Changes
- <what landed>
```
