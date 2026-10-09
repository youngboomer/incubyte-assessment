# CompPulse

Salary management for ACME’s HR manager. The directory is seeded with 10,000 employees and designed to keep working at 100,000.

## Summary
- FastAPI and async SQLAlchemy, SQLite, Next.js
- nginx-proxy-manager publishes the frontend only
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
Application images land in the foundation PR. Until then, this repository is the spec.

When Compose is in place:

- `docker compose -f compose.yaml -f compose.dev.yaml up --build` hosts the frontend on port 65525. The backend listens on 65524 inside the Docker network and has no host port.
- `docker compose up --build` also starts nginx-proxy-manager on ports 80, 443, and 81.

Proxy host, set once in the nginx-proxy-manager UI:

- Forward hostname `frontend`, port `65525`, scheme `http`
- Websockets on
- No proxy host and no location block for the backend

## Commits and pull requests
One summary line, then bullets.

```text
## Summary
<one sentence>

## Changes
- <what landed>
```
