# Performance

Numbers below are from one run of `scripts/check_perf.py` against a private SQLite file of 100,000 employees. The logical suite was running in another process for the first few seconds of the seed. Times are wall clock from that run, not targets copied from the spec.

| Path | Seconds | What it costs |
| --- | ---: | --- |
| Seed 100,000 rows | 26.2032 | O(n). Inserts in batches of 1,000, then one FTS rebuild. |
| Filtered directory page (India, active, salary ascending, limit 50) | 0.0575 | O(limit) after an index seek. 28,641 matched. 50 returned. |
| Keyset page 40 of that filter | 0.0405 | O(limit) after a seek on the sort key and id. Not O(1). The page still had a next cursor. |
| Search `kabir` | 0.0235 | FTS5 prefix query. Not O(1). 3,116 matches. |
| Employee by id | 0.0070 | O(1) primary-key lookup. |
| Analytics overview | 0.8720 | O(n) over active rows. 95,998 active. Seven histogram buckets. Not O(1). |
| Pay update | 0.0196 | O(1) point update plus one audit insert. Version became 2. |
| Stale version | 0.0087 | O(1) rejected write. HTTP 409. The stale reason was not inserted. |
| JPY planning-rate recompute | 0.8139 | O(employees on that currency). Not O(1). Audit rows were not rewritten. |

SQLAlchemy's SQLite dialect renders `OFFSET 0` next to every `LIMIT`. The offset parameter in this run was 0, so the database did not skip rows. The application does not call `offset()`. A non-zero offset fails the script.

The whole program is not O(1). Search, quartiles, the active-salary scan, seeding, and an FX recompute all grow with the rows they touch. A directory page stays O(limit) because the seek uses `(CAST(salary_usd_scaled AS INTEGER), id)` and the id tie-break, then stops at the page size.
