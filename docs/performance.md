# Performance

Numbers below are from one run of `scripts/check_perf.py` against a private SQLite file of 100,000 employees. The run finished with `load_ok` and `EXIT:0`. Times are wall clock from that run. Directory labels are copied from `EXPLAIN QUERY PLAN` of the statements that run made. `row_skip=no` only means the `OFFSET` parameter was 0. It does not mean the plan sought past earlier rows.

| Path | Seconds | What the plan did |
| --- | ---: | --- |
| Seed 100,000 rows | 32.5978 | O(n). Inserts in batches of 1,000, then one FTS rebuild. |
| India, active, salary ascending, first page | 0.0572 | `SEARCH employees USING INDEX idx_emp_status_country (status=? AND country_code=?)` and `USE TEMP B-TREE FOR ORDER BY`. 28,641 matched, 50 returned. This is a filter-index scan plus a sort of the matches. It is not a seek on `idx_emp_salary_usd`, and it is not O(limit). |
| Same filter, keyset page 40 | 0.0416 | The same country/status index and the same temporary sort. The salary predicate does not position that index. Page 40 still had a next cursor. Not O(1). |
| Salary ascending, no country filter, first page | 0.0131 | `SCAN employees USING INDEX idx_emp_salary_usd` with `Rewind:1`. The index is already ordered, and the limit stops the scan. O(limit) for that statement. The request also counts employees by scanning an index. |
| Salary ascending, no country filter, page 40 | 0.0124 | `SEARCH employees USING INDEX idx_emp_salary_usd (<expr>>?)` with `Rewind:0` and `SeekGE`. O(limit) after that seek. Not O(1). A second statement seeks the other direction for the previous cursor (`<expr><`). The count is a separate scan. |
| Search `kabir` | 0.0238 | `SCAN employees_fts VIRTUAL TABLE INDEX 0:M5`, then a temporary B-tree for order. 3,116 matches. FTS prefix search. Not O(1). |
| Employee by id | 0.0066 | `SEARCH employees USING INDEX sqlite_autoindex_employees_1 (id=?)`. O(1) primary key. |
| Analytics overview | 0.8603 | `SEARCH employees USING INDEX idx_emp_status_currency (status=?)` for the active rows, then group and order with temporary B-trees. 95,998 active. Seven histogram buckets. O(n) over active rows. Not O(1). |
| Pay update | 0.0226 | Primary-key lookup, then the point update and one audit insert. Version became 2. O(1). |
| Stale version | 0.0100 | Primary-key lookup. HTTP 409. The stale reason was not inserted (`audit_rows=1` is the successful pay row). O(1). |
| JPY planning-rate recompute | 0.8422 | The employee read is `SCAN employees`. SQLite did not seek a currency index. Not O(1). Audit rows were not rewritten. |

SQLAlchemy's SQLite dialect renders `OFFSET 0` next to every `LIMIT`. The offset parameter in this run was 0. The application does not call `offset()`. A non-zero offset fails the script. The India pages above still sort the filtered matches; a zero offset does not turn that plan into a salary-index seek.

An unfiltered salary page seeks because the comparison is `salary >= ? AND (salary > ? OR id > ?)`, which SQLite plans as `SeekGE` on `idx_emp_salary_usd`. A row-value comparison on the same columns is a rewind from the start of that index. `idx_emp_base_salary` is the same shape for base pay. `tests/test_directory.py::test_salary_keyset_seeks_expression_index` asserts those plans with `EXPLAIN`.

The whole program is not O(1). The India directory page sorts the country/status matches. FTS, quartiles, the active-salary scan, seeding, and the planning-rate recompute all grow with the rows they touch. Only the id lookup, the pay update, and the rejected stale write are O(1). An unfiltered salary page is O(limit) after the index seek, and its total count is not.
