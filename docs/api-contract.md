# API contract

FastAPI paths. The Next.js server calls them with `Authorization: Bearer`. The browser does not. `POST /auth/login` and `GET /health` do not require a token. Every other route returns 401 without one.

Money fields are digit strings plus a scale. `"12000050"` at scale 2 is 120000.50. Clients divide by `10^scale`. Responses do not contain floats.

Unknown fields are ignored only where Pydantic defaults say so. Extra body fields are rejected. Unknown `sort` or `direction` is 422.

## Auth

`POST /auth/login`

```json
{ "email": "hr@acme.test", "password": "compulse-demo" }
```

```json
{ "access_token": "<signed>", "token_type": "bearer" }
```

Wrong credentials: 401 `{ "detail": "Invalid credentials" }`.

`GET /auth/me`

```json
{ "email": "hr@acme.test", "name": "HR Manager" }
```

## Health

`GET /health` → `{ "status": "ok" }`.

## Reference

`GET /reference`

```json
{
  "departments": [{ "id": 1, "name": "Engineering" }],
  "countries": [{ "code": "US", "name": "United States", "currency_code": "USD" }],
  "currencies": [
    {
      "code": "USD",
      "name": "US Dollar",
      "minor_scale": 2,
      "units_per_usd_scaled": "1000000",
      "units_per_usd_scale": 6
    }
  ],
  "levels": ["IC1", "IC2", "IC3", "IC4", "IC5", "M1", "M2"],
  "statuses": ["active", "terminated"]
}
```

## Employees

`GET /employees`

Query: `q`, `department_id`, `country`, `currency`, `status`, `level`, `salary_usd_min`, `salary_usd_max`, `sort`, `direction`, `limit`, `cursor`.

- `status`: `active` or `terminated`. Any other value: 422.
- `level`: one of the `levels` from `/reference`. Any other value: 422.
- `salary_usd_min`, `salary_usd_max`: inclusive bounds on `salary_usd_scaled` (scale 2), compared numerically. Digits only, non-negative, within signed int64. Invalid value or `salary_usd_min` greater than `salary_usd_max`: 422.
- All filters combine with AND, together with `q`, `sort` and `cursor`. `total` counts the filtered set. A cursor is bound to `sort` and `direction`, not to the filters, so keep the same filters while paging.

- `sort`: `name`, `employee_number`, `department`, `country`, `title`, `base_salary`, `salary_usd`, `hire_date`. Default `name`.
- `direction`: `asc` or `desc`. Default `asc`.
- `limit`: 1–100. Default 50.
- `q`: free text. Sanitized into an FTS5 prefix query. Empty after sanitize is ignored.
- `cursor`: opaque. It must match the requested sort and direction, or the response is 422.

```json
{
  "items": [
    {
      "id": "6b1d1a4e-8c0a-4f0e-9c2a-1a2b3c4d5e6f",
      "employee_number": "EMP-00001",
      "first_name": "Ada",
      "last_name": "Okoye",
      "email": "ada.okoye.1@acme.test",
      "job_title": "Software Engineer",
      "department": { "id": 1, "name": "Engineering" },
      "country": { "code": "US", "name": "United States" },
      "currency_code": "USD",
      "level": "IC3",
      "base_salary_scaled": "15500000",
      "variable_pay_scaled": "0",
      "salary_scale": 2,
      "salary_usd_scaled": "15500000",
      "salary_usd_scale": 2,
      "status": "active",
      "hire_date": "2021-03-15",
      "comp_effective_date": "2025-04-01",
      "version_id": 1
    }
  ],
  "next_cursor": null,
  "prev_cursor": null,
  "total": 10000
}
```

`salary_scale` is the currency minor scale and applies to both local salary strings.

`POST /employees`

```json
{
  "first_name": "Ada",
  "last_name": "Okoye",
  "email": "ada.okoye@acme.test",
  "job_title": "Software Engineer",
  "department_id": 1,
  "country_code": "US",
  "level": "IC3",
  "base_salary_scaled": "15500000",
  "variable_pay_scaled": "0",
  "status": "active",
  "hire_date": "2026-01-15",
  "comp_effective_date": "2026-01-15"
}
```

Currency comes from the country. Response is the employee object, `version_id` 1, and the derived `salary_usd_scaled`. Duplicate email or employee number: 409.

`GET /employees/{id}` returns the same employee object. Missing id: 404.

`GET /employees/export.csv` uses the same filters and sort as the directory and ignores `cursor` and `limit`. It returns `text/csv` for every matching row, capped at the active filter, not at one page. Columns: employee number, name, email, title, department, country, currency, level, base major, variable major, USD major, status. Major units are decimal strings produced by `scaled_to_decimal`, not floats.

`GET /employees/{id}/audit` returns newest first.

```json
{
  "items": [
    {
      "id": 10,
      "previous_base_salary_scaled": "15500000",
      "new_base_salary_scaled": "16000000",
      "previous_variable_pay_scaled": "0",
      "new_variable_pay_scaled": "0",
      "salary_scale": 2,
      "currency_code": "USD",
      "fx_units_per_usd_scaled": "1000000",
      "fx_scale": 6,
      "previous_salary_usd_scaled": "15500000",
      "new_salary_usd_scaled": "16000000",
      "salary_usd_scale": 2,
      "reason": "Annual review",
      "effective_date": "2026-04-01",
      "changed_by": "hr@acme.test",
      "created_at": "2026-04-01T09:00:00Z"
    }
  ]
}
```

`PATCH /employees/{id}`

```json
{
  "job_title": "Staff Engineer",
  "department_id": 2,
  "reason": "Promotion",
  "effective_date": "2026-05-01",
  "version_id": 1
}
```

Optional fields: `first_name`, `last_name`, `email`, `job_title`, `department_id`, `level`. At least one is required, and none may be null. Strings are trimmed and must not be empty, `email` must look like an email, `level` must be a known level. Country and currency cannot be changed, and any other field is rejected with 422. `reason` (non-blank), `effective_date` and `version_id` are required. Success returns the employee object with `version_id` incremented and writes one change-log row per field whose value actually changed. If nothing changed, nothing is written and `version_id` stays the same (a stale `version_id` is still 409). Stale `version_id`: 409 `{ "detail": "Record was modified. Reload and try again." }`, nothing written. Duplicate email: 409. Unknown department: 422. Missing id: 404.

`POST /employees/{id}/status`

```json
{
  "status": "terminated",
  "reason": "Resigned",
  "effective_date": "2026-06-30",
  "version_id": 2
}
```

`status` is `active` or `terminated`. `reason` is required and non-blank. Success returns the employee object with `version_id` incremented and one change-log row with `field` `status`. Setting the status the employee already has: 409 `{ "detail": "Employee is already terminated" }`. Stale `version_id`: 409, nothing written. Missing id: 404. Terminated employees drop out of the analytics active set.

`GET /employees/{id}/changes` returns the change log newest first. Rows are append-only. `previous_value` and `new_value` are text. `department_id` changes log department ids.

```json
{
  "items": [
    {
      "id": 4,
      "field": "status",
      "previous_value": "active",
      "new_value": "terminated",
      "reason": "Resigned",
      "effective_date": "2026-06-30",
      "changed_by": "hr@acme.test",
      "created_at": "2026-06-30T09:00:00Z"
    }
  ]
}
```

Missing id: 404.

## Audit feed

`GET /audit` returns pay changes across all employees from `compensation_audit_logs`, newest first (`created_at` desc, then `id` desc). Requires the HR bearer token. Read-only.

Query: `employee_id`, `department_id`, `since`, `until`, `changed_by`, `limit`, `cursor`.

- `since`, `until`: ISO dates `YYYY-MM-DD`, inclusive, compared with `effective_date`. Invalid date or `since` after `until`: 422.
- `changed_by`: exact match. `employee_id` and `department_id` match exactly; an unknown id returns an empty page.
- `limit`: 1–100. Default 50.
- `cursor`: opaque and signed. A malformed, foreign or tampered cursor: 422. Keep the same filters while paging.

Each item has every field of the per-employee audit item above, plus `employee_id`, `employee_number`, `employee_name` (first and last name) and `department`.

```json
{
  "items": [
    {
      "id": 10,
      "employee_id": "6b1d1a4e-8c0a-4f0e-9c2a-1a2b3c4d5e6f",
      "employee_number": "EMP-00001",
      "employee_name": "Ada Okoye",
      "department": { "id": 1, "name": "Engineering" },
      "previous_base_salary_scaled": "15500000",
      "new_base_salary_scaled": "16000000",
      "previous_variable_pay_scaled": "0",
      "new_variable_pay_scaled": "0",
      "salary_scale": 2,
      "currency_code": "USD",
      "fx_units_per_usd_scaled": "1000000",
      "fx_scale": 6,
      "previous_salary_usd_scaled": "15500000",
      "new_salary_usd_scaled": "16000000",
      "salary_usd_scale": 2,
      "reason": "Annual review",
      "effective_date": "2026-04-01",
      "changed_by": "hr@acme.test",
      "created_at": "2026-04-01T09:00:00Z"
    }
  ],
  "next_cursor": null
}
```


## Compensation

`PATCH /employees/{id}/compensation`

```json
{
  "base_salary_scaled": "16000000",
  "variable_pay_scaled": "0",
  "reason": "Annual review",
  "effective_date": "2026-04-01",
  "version_id": 1
}
```

`reason` is required and non-empty. Salary strings must match the employee currency scale. Success returns the employee object with `version_id` incremented. Stale `version_id`: 409 `{ "detail": "Record was modified. Reload and try again." }` and no audit row. Missing id: 404.

## Analytics

`GET /analytics/overview`

Active employees only. Money figures in the payload are USD digit strings at scale 2, except `headcount`.

Optional query parameters narrow the scope. They combine with AND, on top of the active-only rule.

| Param | Meaning |
| --- | --- |
| `department_id` | Integer department id. |
| `country` | Country code, matched exactly (for example `US`). |
| `level` | One of `IC1`, `IC2`, `IC3`, `IC4`, `IC5`, `M1`, `M2`. Anything else: 422. |
| `currency` | Pay currency code, matched exactly (for example `GBP`). |

Every figure in the response, including the breakdowns and the histogram, is computed over the scoped set. An unknown department, country or currency, or a combination that matches nobody, is not an error. It returns the zeroed shape with empty `by_department`, `by_country`, `by_level` and zero-count histogram buckets.

```json
{
  "headcount": 9600,
  "total_salary_usd_scaled": "142000000000",
  "salary_usd_scale": 2,
  "average_salary_usd_scaled": "14791667",
  "p25_salary_usd_scaled": "9000000",
  "p50_salary_usd_scaled": "13000000",
  "p75_salary_usd_scaled": "18000000",
  "by_department": [
    {
      "department_id": 1,
      "department_name": "Engineering",
      "headcount": 3000,
      "total_salary_usd_scaled": "54000000000",
      "average_salary_usd_scaled": "18000000"
    }
  ],
  "by_country": [
    {
      "country_code": "US",
      "country_name": "United States",
      "headcount": 2500,
      "total_salary_usd_scaled": "45000000000",
      "average_salary_usd_scaled": "18000000"
    }
  ],
  "by_level": [
    {
      "level": "IC1",
      "headcount": 900,
      "total_salary_usd_scaled": "4500000000",
      "average_salary_usd_scaled": "5000000",
      "min_salary_usd_scaled": "4000000",
      "p50_salary_usd_scaled": "5000000",
      "max_salary_usd_scaled": "6500000"
    }
  ],
  "histogram": [
    { "label": "0–50k", "count": 400 },
    { "label": "50–75k", "count": 800 },
    { "label": "75–100k", "count": 1200 },
    { "label": "100–150k", "count": 3000 },
    { "label": "150–200k", "count": 2200 },
    { "label": "200–300k", "count": 1500 },
    { "label": "300k+", "count": 500 }
  ]
}
```

`average_salary_usd_scaled` is half-even rounded to cents. Quartiles use `statistics.quantiles(..., n=4, method="inclusive")`.

`by_level` has one entry per level with at least one employee in scope, ordered IC1 to IC5, M1, M2. `p50_salary_usd_scaled` is the inclusive median, half-even rounded to cents like the average. A level with one person reports that salary for min, p50 and max.

## Planning rates

`GET /fx` returns the `currencies` array from `/reference`.

`PATCH /fx/{code}`

```json
{ "units_per_usd_scaled": "84000000" }
```

Scale is 6. The handler recomputes `salary_usd_scaled` for every employee on that currency in the same transaction. Audit USD snapshots do not change. Response is the currency object. Unknown code: 404.

## Errors

| Status | When |
| --- | --- |
| 401 | Missing or bad token, or bad login |
| 404 | Employee or currency not found |
| 409 | Stale `version_id`, duplicate email, or setting the status an employee already has |
| 422 | Validation, bad cursor, bad sort, money that is not a digit string |
