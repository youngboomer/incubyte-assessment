# Directory API

## Summary
Search, filter, and keyset-paginate employees.

## Owns
- `GET /employees`, `GET /employees/{id}`, `GET /reference`, `GET /employees/export.csv`
- FTS query builder and keyset cursor
- Tests for those routes

## Does not touch
- Compensation updates, analytics aggregates, the seed generator

## Rules
- FTS5 prefix query, sanitized. A query containing `"` or `:` returns 200, not 500
- Sort allow-list from `docs/api-contract.md`. Salary order uses `CAST(salary_usd_scaled AS INTEGER)` so `"99"` sorts before `"100"`
- Cursor seeks. No `OFFSET`
- CSV uses `scaled_to_decimal` for major-unit columns
- Register the router on the existing registry line only

## Done when
- Page size, combined filters, bad sort, bad cursor, and numeric salary order are tested
- Missing id is 404. No token is 401
