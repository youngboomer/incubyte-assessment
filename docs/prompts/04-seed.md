# Seed

## Summary
Deterministic employees, default 10,000, able to run at 100,000.

## Owns
- `python -m app.seed` and the fixed name tuples
- Startup seed when the employee table is empty
- The golden seed test

## Does not touch
- Routers other than the startup hook

## Rules
- `random.Random(42)` only. No Faker
- Emails `{first}.{last}.{n}@acme.test`. Numbers `EMP-00001` upward
- About 4% terminated. Sales carries variable pay. Other shape notes are in `docs/architecture.md`
- Store money only through `decimal_to_scaled`, then re-derive USD with the same converter
- Batches of 1,000, then one FTS rebuild
- Default count 10,000. `--count 100000` and `--reset` work

## Done when
- CI seeds 10,000 and checks count, one golden row, the digit-string pattern, and the USD invariant
- A tiny fixture proves salary sort orders `"99"` before `"100"`
