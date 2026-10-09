# Architecture

## Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, `sqlite+aiosqlite`.
- Database: one SQLite file. The brief seeds 10,000 employees. Indexes, search, and pagination are built so 100,000 rows do not force a rewrite.
- Frontend: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Table, Recharts.
- Deploy: Docker Compose and nginx-proxy-manager. Only the proxy publishes host ports.

Routes that perform I/O are `async def` and `await` an `AsyncSession`. A blocking SQLite call does not run on the event loop. `aiosqlite` runs the file driver on a worker thread under that async API. One Uvicorn worker, because SQLite has a single writer. WAL and `busy_timeout` cover a rare overlapping write. This scales row count for one HR user. Many hosts writing at once would be Postgres, which this submission does not need.

```python
engine = create_async_engine(
    settings.database_url,  # sqlite+aiosqlite:////data/comppulse.db
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)
```

`NullPool` avoids a QueuePool of SQLite connections across tasks. On every connection, via `engine.sync_engine`:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

`metadata.create_all` does not create FTS5 tables or triggers. The schema initializer does.

Layering:

- Routers map HTTP and raise `fastapi.HTTPException`.
- Services own transactions and rules.
- Repositories own SQL and return data or a typed not-found / version-conflict. They do not raise HTTP exceptions.

No CORS. The browser never calls FastAPI.

## Network

```text
Internet
  └─ nginx-proxy-manager     host ports 80, 443, 81
        └─ network: web
             └─ frontend     Next.js :3000, no host ports
                  └─ network: internal
                       └─ backend   FastAPI :8000, no host ports
                            └─ volume: /data/comppulse.db
```

`internal` is a Compose network with `internal: true`. The backend is attached only to that network, so the proxy cannot route to it and the host cannot open port 8000. The frontend is on both networks and calls `BACKEND_URL=http://backend:8000` from the server. `BACKEND_URL` is not a `NEXT_PUBLIC_` variable.

Login: FastAPI checks `HR_EMAIL` and `HR_PASSWORD` and returns a bearer token signed with `itsdangerous.TimestampSigner` and `APP_SECRET`, max age `TOKEN_MAX_AGE_SECONDS`. The Next.js login action stores it in the httpOnly cookie `comppulse_session`. Later server calls send `Authorization: Bearer`. Logout deletes the cookie. `POST /auth/login` and `GET /health` are the only unauthenticated routes.

`compose.yaml` runs proxy, frontend, and backend. `compose.dev.yaml` publishes frontend port 3000 and does not start the proxy. The backend stays unpublished.

nginx-proxy-manager (`jc21/nginx-proxy-manager`) has one proxy host: forward hostname `frontend`, port `3000`, scheme `http`, websockets on. No second name. No location block for the backend.

## Money

SQLite has no DECIMAL type. A numeric affinity stores a float. Money is a TEXT column of scaled digits, matching `^-?\d+$`, with no decimal point and no exponent. The scale says how to divide it into a `Decimal`.

```text
"12000050"  scale 2  →  Decimal("120000.50")
"8000000"   scale 0  →  Decimal("8000000")     # JPY
"780000"    scale 6  →  Decimal("0.78")        # GBP units per 1 USD
```

`app/money.py` is the only converter.

```python
def scaled_to_decimal(scaled: str, scale: int) -> Decimal:
    return Decimal(scaled) / (Decimal(10) ** scale)

def decimal_to_scaled(amount: Decimal, scale: int) -> str:
    factor = Decimal(10) ** scale
    digits = (amount * factor).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return format(digits, "f")
```

`"12.00"`, `"1e5"`, and `""` are rejected. Values that do not fit in a signed 64-bit integer are rejected, so `CAST(salary_usd_scaled AS INTEGER)` cannot truncate. API JSON returns the digit string and the scale. Clients divide. They do not receive a float.

USD pay stored on the employee:

```text
local = scaled_to_decimal(base, scale) + scaled_to_decimal(variable, scale)
usd   = local / scaled_to_decimal(units_per_usd_scaled, 6)
salary_usd_scaled = decimal_to_scaled(usd, 2)
```

`salary_usd_scaled` is rewritten in the same transaction as a local pay change or a planning-rate change. The canonical amount is the local digit string. Audit rows copy the USD string and the rate string at write time, so a later rate edit does not rewrite history.

Sample planning rates (local major units per 1 USD):

| Code | Scale | Units per USD | `units_per_usd_scaled` |
| --- | --- | --- | --- |
| USD | 2 | 1 | `1000000` |
| GBP | 2 | 0.78 | `780000` |
| EUR | 2 | 0.92 | `920000` |
| INR | 2 | 83.50 | `83500000` |
| SGD | 2 | 1.34 | `1340000` |
| JPY | 0 | 149 | `149000000` |
| CAD | 2 | 1.36 | `1360000` |
| AUD | 2 | 1.52 | `1520000` |

These are labeled sample planning rates in the UI, not spot rates.

## Schema

`employees` keeps the implicit `rowid`. It is not `WITHOUT ROWID`. FTS5 joins on `rowid`, not on the UUID.

```sql
CREATE TABLE currencies (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  minor_scale INTEGER NOT NULL,
  units_per_usd_scaled TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE countries (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  currency_code TEXT NOT NULL REFERENCES currencies(code)
);

CREATE TABLE departments (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE employees (
  id TEXT PRIMARY KEY,
  employee_number TEXT NOT NULL UNIQUE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  job_title TEXT NOT NULL,
  department_id INTEGER NOT NULL REFERENCES departments(id),
  country_code TEXT NOT NULL REFERENCES countries(code),
  currency_code TEXT NOT NULL REFERENCES currencies(code),
  level TEXT NOT NULL,
  base_salary_scaled TEXT NOT NULL,
  variable_pay_scaled TEXT NOT NULL,
  salary_usd_scaled TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'terminated')),
  hire_date TEXT NOT NULL,
  comp_effective_date TEXT NOT NULL,
  version_id INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE compensation_audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id TEXT NOT NULL REFERENCES employees(id),
  previous_base_salary_scaled TEXT NOT NULL,
  new_base_salary_scaled TEXT NOT NULL,
  previous_variable_pay_scaled TEXT NOT NULL,
  new_variable_pay_scaled TEXT NOT NULL,
  currency_code TEXT NOT NULL,
  fx_units_per_usd_scaled TEXT NOT NULL,
  previous_salary_usd_scaled TEXT NOT NULL,
  new_salary_usd_scaled TEXT NOT NULL,
  reason TEXT NOT NULL,
  effective_date TEXT NOT NULL,
  changed_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_emp_status_dept ON employees(status, department_id);
CREATE INDEX idx_emp_status_country ON employees(status, country_code);
CREATE INDEX idx_emp_status_currency ON employees(status, currency_code);
CREATE INDEX idx_emp_salary_usd ON employees (CAST(salary_usd_scaled AS INTEGER), id);
```

Text sort would order `"99"` after `"100"`. Salary order and keyset seeks use `CAST(salary_usd_scaled AS INTEGER)` so they match the index.

Audit immutability:

```sql
CREATE TRIGGER compensation_audit_logs_no_update
BEFORE UPDATE ON compensation_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'audit log is append-only');
END;

CREATE TRIGGER compensation_audit_logs_no_delete
BEFORE DELETE ON compensation_audit_logs
BEGIN
  SELECT RAISE(ABORT, 'audit log is append-only');
END;
```

## Optimistic concurrency

```sql
UPDATE employees
SET base_salary_scaled = :base,
    variable_pay_scaled = :variable,
    salary_usd_scaled = :usd_scaled,
    comp_effective_date = :effective_date,
    version_id = version_id + 1,
    updated_at = :now
WHERE id = :id AND version_id = :expected;
```

The audit insert commits in the same transaction.

- One row updated: return the new profile and version.
- Zero rows and the id exists: HTTP 409, no audit row.
- Zero rows and the id is missing: HTTP 404.

The UI shows the 409 and reloads. It does not retry the write.

## Search

FTS5, external content, `unicode61` with diacritics removed. Porter stemming folds personal names and is not used.

```sql
CREATE VIRTUAL TABLE employees_fts USING fts5(
  employee_number, first_name, last_name, email, job_title,
  content='employees',
  content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 2'
);
```

Insert, update, and delete triggers keep the index aligned with `employees`. Application code does not dual-write it. The seed bulk-loads employees, then `INSERT INTO employees_fts(employees_fts) VALUES('rebuild')`.

The query builder strips `" * : ^ ( )`, splits on whitespace, drops empty tokens, appends `*` to each token, and joins with `AND`. An empty sanitize result skips FTS. The `MATCH` target is the FTS alias.

## Quartiles and totals

`SUM` and `COUNT` run in SQL on `CAST(salary_usd_scaled AS INTEGER)`. SQLite `AVG` returns a float, so the mean is `Decimal(sum_cents) / 100 / count` in Python. Totals ignore terminated employees.

Quartiles do not use `MIN(CASE WHEN percent_rank >= 0.25 ...)`. That expression is not Excel `PERCENTILE.INC` and not PostgreSQL `PERCENTILE_CONT`.

The service loads `(department_id, country_code, salary_usd_scaled)` for active employees, converts with `scaled_to_decimal(..., 2)`, and calls `statistics.quantiles(values, n=4, method="inclusive")`. At 100,000 rows that column is a couple of megabytes. The position formula is `1 + (n - 1) * p`, with linear interpolation, which is what `method="inclusive"` implements. Past a few million rows this would move into SQL. That is not this product.

Histogram buckets in USD: 0–50k, 50–75k, 75–100k, 100–150k, 150–200k, 200–300k, 300k+.

## Pagination

Keyset, not offset. A deep `OFFSET` walks every skipped row. The cursor is an opaque encoding of the sort name, direction, edge sort values, and `id`. The following page seeks with a tuple comparison. `id` breaks ties. The response includes `next_cursor`, `prev_cursor`, and `total`. Limit max is 100.

## Seed

`random.Random(42)` and fixed name tuples in the repo. No Faker. Default count is 10,000. `--count 100000` uses the same generator. Emails are `{first}.{last}.{n}@acme.test`. Employee numbers are `EMP-00001` onward.

Shape: country weight toward India and the US; level pyramid with many IC2/IC3 and few M2; Engineering the largest department; about 4% terminated; Sales variable pay at 10–20% of base. Local amounts are rounded to a payroll increment, stored through `decimal_to_scaled`, then USD is re-derived so the stored string matches the converter. Inserts are batches of 1,000. Startup seeds 10,000 when the table is empty.

## What this document will not claim

Latency numbers come from `scripts/check_perf.py` at 100,000 rows and are written into `docs/performance.md` after a real run. CI seeds 10,000 and does not assert milliseconds.
