# Compensation API

## Summary
Change pay with a version check, and keep an append-only audit trail.

## Owns
- `PATCH /employees/{id}/compensation`
- `GET /employees/{id}/audit`
- `PATCH /fx/{code}` and `GET /fx`
- Audit immutability triggers
- `POST /employees` if the foundation did not already create rows through the seed
- Tests for those routes

## Does not touch
- FTS query SQL, analytics overview

## Rules
- Salary update and audit insert commit together, or not at all
- Stale `version_id` is 409 and writes nothing. Missing id is 404
- Audit stores the USD string and `fx_units_per_usd_scaled` from the moment of the change
- A later FX patch recomputes `salary_usd_scaled` and does not change audit USD snapshots
- Triggers abort `UPDATE` and `DELETE` on `compensation_audit_logs`
- Use `app/money.py`. Do not reimplement rounding

## Done when
- Success bumps `version_id` and returns the new profile
- Conflict, not-found, FX recompute, and trigger tests pass
