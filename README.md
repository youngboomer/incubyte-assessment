# CompPulse

Salary management for ACME's HR manager. Find any of 10,000 employees, change pay with a recorded reason, edit details, terminate or reactivate people, and answer how the company pays people. Seeded with 10,000 employees and built to keep working at 100,000.

## What it does
- **Employees:** search by name, email or employee number. Filter by country, department, level, status and a US dollar pay range. Sort, page, export the filtered view to CSV.
- **Add and edit:** add an employee (currency follows the country), edit title, department and level, terminate or reactivate with a date and a reason.
- **Change pay:** base and variable pay with an effective date and a mandatory reason, a live preview in US dollars, and a clear message when someone else changed the record first.
- **History:** every pay change and every detail change (level, title, department, name, email, terminate and reactivate) is logged with who, when and why, and pay changes also keep the exchange rate used. Change history has a Pay tab and a Details tab with filters. The logs are append-only.
- **Pay overview:** headcount, total, average and middle pay, a pay range bar, a distribution chart, pay by level, and breakdowns by department and country, with filters.
- **Planning rates:** one exchange rate per currency. Changing one recalculates everyone paid in it; past history keeps the rate it used.
- **Phone to desktop:** one fluid layout. Tables become cards and the menu collapses.

## How it is built
```text
Browser --HTTPS--> reverse proxy --> web (Next.js, 127.0.0.1:65525) --> API (FastAPI, internal network) --> SQLite
```
- The browser never talks to the API. The web server holds the session cookie and calls the API with a signed token.
- Backend: FastAPI, async SQLAlchemy, SQLite with full-text search. Money is stored as digit strings with a scale, never floats.
- Web: Next.js, plain CSS, a typed data layer and a small shared design system. No UI kit.
- Docker Compose runs two containers. The API has no published port.

## Docs
- `docs/prd.md` goal, scope, exclusions
- `docs/architecture.md` schema, money, search, concurrency, network
- `docs/api-contract.md` request and response shapes
- `docs/performance.md` measured cost of the 100,000-row paths
- `docs/verification-report.md` and `.html` second pass and test evidence
- `docs/ai-usage.md` how the agents and local checks were used
- `docs/prompts/` PR specs for the build
- `todo.md` known gaps and planned work

## Run locally
```bash
cp .env.example .env        # sets APP_ENV=development and the demo login
docker compose up --build   # http://127.0.0.1:65525
```
Demo login: `ss@interview.chetan` / `incubyte`. It works only with `APP_ENV=development`.

Without a `.env`, compose defaults to `APP_ENV=production` and the API refuses to start with `insecure_config`. That is intended.

Seed data: 10,000 employees with unique, country-matched names from `backend/app/names.json`. The file holds only the names the seed uses, and you can edit it by hand. `scripts/build_names.py` dumps it from a larger dataset once and will not overwrite it without `--force`. Reset the data with `python -m app.seed --reset`.

## Tests
```bash
cd backend && pytest                      # 305 tests
cd web && npm test                        # 91 unit tests
cd web && node --experimental-strip-types --test proxy-rules.test.ts   # 6 login-gate tests
```
Backend coverage is about 96%. Lint: `cd backend && ruff check .`.

## Deploy
Create `.env` next to `compose.yaml` (it is git-ignored) with:
- `APP_ENV=production`
- `APP_SECRET`: random, 32 or more characters
- `HR_EMAIL`
- `HR_PASSWORD_HASH`: from `python -m app.passwords <password>`, single-quoted because it contains `$`

Then `docker compose up -d --build`. Production refuses to start without these, and refuses a plain password.

- **Proxy:** forward to `127.0.0.1:65525`, redirect HTTP to HTTPS, and forward `X-Real-IP`. The API reads the visitor address from it for the login limit.
- **Limits:** the two containers together stay within 0.75 CPU and 500 MB (API 0.45 CPU and 300 MB, web 0.30 CPU and 200 MB), with swap off, 100 processes each and rotated logs. A runaway load can only slow or restart these containers.
- **Data:** SQLite lives in the `db_data` volume. There is no backup job.
- **Volume ownership:** containers run as non-root. A volume created by an older, root-run version must be recreated once with `docker compose down -v`; demo data is reseeded.

## Security
- TLS at the proxy. The API is on an internal network with no published port; the web container listens on `127.0.0.1` only.
- Passwords are stored as scrypt hashes and compared in constant time. Tokens are signed and expire after 12 hours. Logout revokes the token in the database, so it stays revoked after a restart.
- The session cookie is HttpOnly, Secure and SameSite=Lax. The token never reaches browser scripts.
- Five failed logins lock that visitor out for five minutes. The limit is per visitor address.
- Every API route needs the token except health and login. The web app blocks every page by default, and the API checks the token again.
- All SQL uses bound parameters, sort columns come from a fixed list, writes reject unknown fields, and every text input has a length limit.
- Content-Security-Policy, frame, content-type, referrer, permissions and HSTS headers are set. CSV cells that start with a formula character are neutralised.
- Containers run as a normal user with all capabilities dropped, no privilege escalation and a read-only filesystem.
- History tables are append-only: the database refuses updates and deletes.

Known gaps: no rate limiting at the proxy, one shared login without roles, the database is not encrypted at rest, and dependency versions are not pinned.

## Demo video
About three minutes against the running site.

1. Log in as `ss@interview.chetan` / `incubyte`.
2. Search the directory, filter to one country and open a person. Local pay is the stored base and variable amount. US dollars is local pay divided by the planning rate at the time it was saved.
3. Change pay with a reason and an effective date. Show the new history entry with local pay, US dollars and the planning rate.
4. Open Change pay in two tabs and save in both. The second says `Someone else changed this record while you were editing. Nothing was saved.`
5. Open Pay overview. Read headcount, total, average, the quartiles and pay by level, then filter by country.
6. Change a planning rate and show the US dollar figures update.

## Commits and pull requests
One summary line, then bullets.

```text
## Summary
<one sentence>

## Changes
- <what landed>
```
