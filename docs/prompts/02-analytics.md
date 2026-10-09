# Analytics API

## Summary
Org pay totals, inclusive quartiles, and the USD histogram.

## Owns
- `GET /analytics/overview` and `app/stats.py`
- Tests against a hand-built fixture

## Does not touch
- Employee mutations, FTS SQL, the seed generator

## Rules
- Active employees only
- `SUM` and `COUNT` on `CAST(salary_usd_scaled AS INTEGER)`. Mean is `Decimal`, not SQLite `AVG`
- Quartiles: `statistics.quantiles(..., n=4, method="inclusive")` after `scaled_to_decimal(..., 2)`
- Pin p25, p50, and p75 on a sorted fixture that includes a tie and an even count
- Histogram labels match `docs/api-contract.md`

## Done when
- The fixture quartiles match the hand calculation
- A terminated employee is excluded from headcount and total
