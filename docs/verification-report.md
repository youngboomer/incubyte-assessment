# CompPulse verification report

Date: 2026-10-09. Stack under test: Compose frontend on `127.0.0.1:65525`, backend on the internal Docker network only. Evidence is quoted from the captured runs. A line is marked pass only when that run printed it.

## Scope checked

Checked against `docs/prd.md`, `docs/architecture.md`, and `docs/api-contract.md` after the directory, dashboard, and profile screens were on `main`.

Exercised:

- Login as `hr@acme.test`, filtered directory, keyset-backed pages, CSV of that filter, add-employee path covered by the directory suite, profile local pay and USD, pay change with reason and effective date, append-only audit, stale version, planning-rate edit, and the active-employee dashboard.
- Backend suite on its own temporary databases: money conversion, FTS sanitizer, keyset directory, inclusive quartiles, half-even mean, compensation conflict, FX recompute, audit immutability, and the 10,000-row seed.
- A separate 100,000-row process on its own SQLite file.
- Server-rendered HTML for login, directory, dashboard, profile, and FX, including empty, error, and conflict states.

Out of this run: the demo video, nginx-proxy-manager (it is not running on this machine), and GitHub Actions (the account billing limit stops the jobs before they execute).

## Second pass

Each locked rule has a citation from a test name or a captured response.

| Rule | Result | Citation |
| --- | --- | --- |
| Money is a scaled digit string. JSON does not carry salary floats. | Pass | `tests/test_money.py::test_scaled_usd_cents` PASSED. `tests/test_money.py::test_rejects_float_amount` PASSED. `tests/test_money.py::test_rejects_non_digit_strings[12.00]` and `[1e5]` PASSED. `e2e.log`: `directory_status=200 country=IN status=active scaled_digit_strings=True`. The directory and profile checks rejected float JSON fields before that line was written. |
| Search is FTS5 (`unicode61 remove_diacritics 2`), not Porter and not a search `LIKE`. | Pass | `tests/test_directory.py::test_sanitize_fts_query` PASSED. `tests/test_directory.py::test_query_with_quotes_and_colon_returns_200` PASSED. `load.log`: `search_page seconds=0.0238 offset_param=0 row_skip=no complexity=FTS-prefix-not-O(1)` and `search_total=3116`. The plan is `SCAN employees_fts VIRTUAL TABLE INDEX 0:M5`. Employee-number allocation still uses `LIKE 'EMP-%'`. That statement is not the directory search. |
| Directory pages are keyset cursors. The application does not skip rows with a non-zero OFFSET. An unfiltered salary page seeks `idx_emp_salary_usd`. The India/active salary page does not. | Pass | `tests/test_directory.py::test_page_size_and_keyset` PASSED. `tests/test_directory.py::test_salary_keyset_seeks_expression_index` PASSED. That test runs `EXPLAIN` on the shipped page SQL and requires `SEARCH employees USING INDEX idx_emp_salary_usd (<expr>` with `SeekGE`, the descending page with `SeekLE`, and no `Rewind`. The same test requires `idx_emp_base_salary` and `SeekGE` for base pay. `load.log`: `salary_seek_page plan[0]=SEARCH employees USING INDEX idx_emp_salary_usd (<expr>>?)` and `opcodes=Rewind:0,SeekGE:3`. `filtered_page plan[0]` and `deep_keyset_page plan[0]` are `SEARCH employees USING INDEX idx_emp_status_country (status=? AND country_code=?)` plus `USE TEMP B-TREE FOR ORDER BY`. Both record `offset_param=0 row_skip=no`. SQLAlchemy still renders `OFFSET 0`. The application source does not call `offset()`. |
| A stale `version_id` returns 409 and writes no audit row. | Pass | `tests/test_compensation.py::test_stale_version_is_409_and_writes_nothing` printed `409 detail=Record was modified. Reload and try again. audit_reasons=[('First',)]` and PASSED. `e2e.log`: `stale_message=Record was modified. Reload and try again.` and `audit_after_stale raise=6 stale=0`. `load.log`: `stale_status=409 audit_rows=1` after one successful pay update. The stale reason was not inserted. |
| Quartiles use inclusive percentiles. | Pass | `tests/test_analytics.py::test_quartiles_exclude_terminated_employee` printed `inclusive quartiles p25=5000000 p50=6500000 p75=11000000` and PASSED. The fixture salaries are 40000, 50000, 50000, 80000, 120000, and 300000. |
| The mean is a `Decimal`. The overview does not use SQLite `AVG`. | Pass | `tests/test_analytics.py::test_mean_half_even` PASSED. That fixture expects Engineering average `"100"` and Finance average `"102"`. `backend/app/stats.py` computes `Decimal(sum_cents) / Decimal(100) / Decimal(count)`. No `AVG` call is in the application package. |
| The seed is deterministic, the default count is 10,000, and 100,000 rows load. | Pass | `backend/app/settings.py` sets `seed_count: int = 10000`. `backend/app/seed.py` uses `Random(42)`. `tests/test_seed.py::test_seed_ten_thousand_golden_row_and_invariants` printed `USD invariant held for 10000 rows` and PASSED. `tests/test_seed.py::test_seed_without_reset_keeps_a_changed_planning_rate` PASSED. `load.log`: `seed count=100000 seconds=32.5978 complexity=O(n)` and `load_ok` with `EXIT:0`. |
| The browser does not call FastAPI. | Pass | `e2e.log` drives `http://127.0.0.1:65525` and records `login_status=303 cookie=comppulse_session`. `ui.log`: `method=server-rendered HTML through http://127.0.0.1:65525`. `launch.log`: `container_health={"status":"ok"}` from inside the frontend container. `web/lib/api.ts` throws if `window` is defined. |
| The backend has no host port. | Pass | `launch.log` lists `comppulse-backend` with an empty PORTS column and `comppulse-frontend` as `127.0.0.1:65525->65525/tcp`. The same log records `HOST_65524=closed`. A repeat of the frontend GET is the second `HTTP/1.1 200 OK` with `front2 CompPulse=True health=True`. |

`tests/test_directory.py::test_salary_numeric_order` printed `salary order "99" before "100"` and PASSED. `tests/test_compensation.py::test_fx_recompute_does_not_rewrite_audit_snapshots` PASSED.

## Logical

Command result captured in `logical-tests.log`, after the hyphen split was in the tree:

- `All checks passed!`
- `RUFF_EXIT:0`
- `86 passed in 7.33s`
- `PYTEST_EXIT:0`

The run also printed the four locked strings named in the verification plan: the 409 detail and `audit_reasons=[('First',)]`, `salary order "99" before "100"`, `inclusive quartiles p25=5000000 p50=6500000 p75=11000000`, and `USD invariant held for 10000 rows`.

`tests/test_directory.py::test_salary_keyset_seeks_expression_index` PASSED in that run. The hyphen assertions remain inside `test_sanitize_fts_query` and `test_query_with_quotes_and_colon_returns_200`.

## E2E

`e2e.log` ends with `e2e_ok`. The client posted multipart forms to the Next server and followed the redirects. It did not call port 65524.

```text
login_document product=CompPulse health={"status":"ok"}
login_status=303 cookie=comppulse_session
directory_status=200 country=IN status=active scaled_digit_strings=True
profile_url=/employees/1ac586b2-3e42-24ca-6e63-158e1c0f4ef4
pay_change_status=303 version_sent=3
audit_e2e_raise_count=6
stale_message=Record was modified. Reload and try again.
audit_after_stale raise=6 stale=0
dashboard_status=200 sections=headcount,total,average,p25,p50,p75,histogram
empty_directory=No employees match these filters.
directory_error=Could not load employees.
fx_notice=present currencies=USD,EUR,INR,JPY
csv_export=200 rows=2829
e2e_ok
```

`audit_e2e_raise_count` and `raise=6` are counts of the text `E2E raise` in the profile HTML. `stale=0` is the count of the text `E2E stale` on a fresh profile GET after the rejected write. The script exits if that stale text is present.

The saved dashboard document from that same run renders the overview payload: Headcount 9576, Total `$$1,214,039,285.14`, Average `$$126,779.37`, P25 `$$83,148.20`, P50 `$$114,137.58`, P75 `$$163,991.02`, and a histogram label `0–50k` (en dash). Those figures are the live 10,000-row database after the pay edits in this session, not a series written into the page source.

The filtered CSV returned 2,829 data rows through the Next export route for the India active filter.

## UI/UX

No desktop browser was available. `ui.log` records `browser=not-used` and ends with `ui_ok`. The check used the server-rendered HTML from the same Next origin as the end-to-end run.

```text
browser=not-used
method=server-rendered HTML through http://127.0.0.1:65525
login=CompPulse and live {"status":"ok"}
empty=No employees match these filters.
error=Could not load employees.
conflict=Record was modified. Reload and try again. Reload link present. No second audit row.
fx-notice=present and currencies came back as USD EUR INR JPY
dashboard=headcount total average quartiles histogram from the overview payload
hardcoded-series=none observed; empty search changed the directory result
ui_ok
```

The empty search was `q=zzzz-no-such-person-e2e`. After the hyphen split, that query returns HTTP 200 and the empty-state sentence. A bad cursor still renders `Could not load employees.` The FX page lists USD, EUR, INR, and JPY from the reference payload, and it includes the sentence that saving recomputes USD pay while audit history keeps the original rate. The add-employee hint `for example 120000.50` is format copy. It is not a person or a total.

## Stress/load

`load.log` is a separate process and a separate database. It ends with `load_ok` and `EXIT:0`. This run is after the salary-seek change. The script prints `EXPLAIN QUERY PLAN` and the `EXPLAIN` opcode counts for each statement. `row_skip=no` means the offset parameter was 0.

```text
seed count=100000 seconds=32.5978 complexity=O(n)
filtered_page seconds=0.0572 offset_param=0 row_skip=no complexity=filter-index-scan-plus-sort-not-salary-seek-not-O(1) statements=2
filtered_page plan[0]=SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH employees USING INDEX idx_emp_status_country (status=? AND country_code=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) ; USE TEMP B-TREE FOR ORDER BY opcodes=Rewind:0,SeekGE:3,SeekLE:0,SeekGT:0,SeekLT:0
filtered_page plan[1]=SEARCH employees USING COVERING INDEX idx_emp_status_country (status=? AND country_code=?) opcodes=Rewind:0,SeekGE:1,SeekLE:0,SeekGT:0,SeekLT:0
filtered_page total=28641 items=50
deep_keyset_page seconds=0.0416 offset_param=0 row_skip=no complexity=filter-index-scan-plus-sort-not-salary-seek-not-O(1) statements=3
deep_keyset_page plan[0]=SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH employees USING INDEX idx_emp_status_country (status=? AND country_code=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) ; USE TEMP B-TREE FOR ORDER BY opcodes=Rewind:0,SeekGE:3,SeekLE:0,SeekGT:0,SeekLT:0
deep_page_reached pages=40 items=50 has_next=True
salary_first_page seconds=0.0131 offset_param=0 row_skip=no complexity=O(limit)-ordered-salary-index-scan-not-O(1) statements=2
salary_first_page plan[0]=SCAN employees USING INDEX idx_emp_salary_usd ; SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) opcodes=Rewind:1,SeekGE:2,SeekLE:0,SeekGT:0,SeekLT:0
salary_seek_page seconds=0.0124 offset_param=0 row_skip=no complexity=O(limit)-after-salary-index-seek-not-O(1) statements=3
salary_seek_page plan[0]=SEARCH employees USING INDEX idx_emp_salary_usd (<expr>>?) ; SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) opcodes=Rewind:0,SeekGE:3,SeekLE:0,SeekGT:0,SeekLT:0
salary_seek_reached pages=40 items=50 has_next=True
search_page seconds=0.0238 offset_param=0 row_skip=no complexity=FTS-prefix-not-O(1) statements=2
search_page plan[0]=SEARCH employees USING INTEGER PRIMARY KEY (rowid=?) ; LIST SUBQUERY 1 ; SCAN employees_fts VIRTUAL TABLE INDEX 0:M5 ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) ; USE TEMP B-TREE FOR ORDER BY opcodes=Rewind:1,SeekGE:2,SeekLE:0,SeekGT:0,SeekLT:0
search_total=3116
id_lookup seconds=0.0066 offset_param=absent row_skip=no complexity=O(1)-primary-key statements=1
id_lookup plan[0]=SEARCH employees USING INDEX sqlite_autoindex_employees_1 (id=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) opcodes=Rewind:0,SeekGE:3,SeekLE:0,SeekGT:0,SeekLT:0
analytics seconds=0.8603 offset_param=absent row_skip=no complexity=O(n)-active-rows-not-O(1) statements=4
analytics plan[0]=SEARCH employees USING INDEX idx_emp_status_currency (status=?) opcodes=Rewind:0,SeekGE:1,SeekLE:0,SeekGT:0,SeekLT:0
analytics_headcount=95998 histogram=7
pay_update seconds=0.0226 offset_param=absent row_skip=no complexity=O(1)-point-update-plus-audit-insert statements=4
pay_update plan[0]=SEARCH employees USING INDEX sqlite_autoindex_employees_1 (id=?) ; SEARCH departments USING INTEGER PRIMARY KEY (rowid=?) ; SEARCH countries USING INDEX sqlite_autoindex_countries_1 (code=?) ; SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) opcodes=Rewind:0,SeekGE:3,SeekLE:0,SeekGT:0,SeekLT:0
pay_version=2
stale_version seconds=0.0100 offset_param=absent row_skip=no complexity=O(1)-rejected-write statements=3
stale_status=409 audit_rows=1
fx_recompute seconds=0.8422 offset_param=absent row_skip=no complexity=O(employees-on-currency)-not-O(1) statements=4
fx_recompute plan[1]=SEARCH currencies USING INDEX sqlite_autoindex_currencies_1 (code=?) ; SCAN employees opcodes=Rewind:1,SeekGE:1,SeekLE:0,SeekGT:0,SeekLT:0
load_ok
EXIT:0
```

Thirty-nine `keyset_step` lines sit between the first India page and `deep_page_reached`. Each is `filter-index-scan-plus-sort-not-salary-seek-not-O(1)` and `offset_param=0 row_skip=no`. Thirty-nine `salary_seek_step` lines sit before `salary_seek_reached`. Each is `O(limit)-after-salary-index-seek-not-O(1)`. The `SeekGE` count on the India plan is the country index and the joins. That plan does not name `idx_emp_salary_usd`.

The planning-rate line's complexity token says `O(employees-on-currency)`. Its plan says `SCAN employees`. The scan reads the employee table. It is not O(1).

## Profile

The whole program is not O(1). Costs below follow the plans in `load.log`, not a label chosen ahead of the run.

| Path | Seconds | Rows touched | Cost |
| --- | ---: | --- | --- |
| Seed | 32.5978 | 100,000 inserted | O(n). Batches of 1,000, then one FTS rebuild. |
| India, active, salary page | 0.0572 | 28,641 matched, 50 returned | `idx_emp_status_country` plus `USE TEMP B-TREE FOR ORDER BY`. A filter-index scan and a sort of the matches. Not a salary-index seek. Not O(limit). Not O(1). |
| India keyset page 40 | 0.0416 | 50 returned, next cursor present | Same country/status index and the same sort. The salary bound does not position that index. Not O(1). |
| Salary page, no filter, first page | 0.0131 | 50 returned | `SCAN idx_emp_salary_usd` with `Rewind:1`, stopped by the limit. O(limit) for that statement. The count scans an employees index. |
| Salary page 40, no filter | 0.0124 | 50 returned, next cursor present | `SEARCH idx_emp_salary_usd (<expr>>?)`, `Rewind:0`, `SeekGE`. O(limit) after the seek. Not O(1). |
| Search `kabir` | 0.0238 | 3,116 matches | FTS5 virtual-table scan, then a sort. Not O(1). |
| Employee by id | 0.0066 | 1 | O(1) primary-key lookup. |
| Analytics overview | 0.8603 | 95,998 active, 7 histogram buckets | `idx_emp_status_currency` over active rows. O(n). Not O(1). |
| Pay update | 0.0226 | version became 2 | O(1) primary-key update plus one audit insert. |
| Stale version | 0.0100 | HTTP 409, `audit_rows=1` | O(1) rejected write. The audit row is the successful pay change. |
| Planning-rate recompute | 0.8422 | `SCAN employees` | Table scan, then primary-key updates. Not O(1). |

`tests/test_directory.py::test_salary_keyset_seeks_expression_index` is the check that base pay seeks `idx_emp_base_salary` with `SeekGE` and that a descending USD page uses `SeekLE`. The 100,000-row script measured USD salary, not base pay.

`OFFSET 0` in the rendered SQL is the SQLite dialect default when the query has a limit and no offset clause. `row_skip=no` means the bound value was 0. A non-zero offset fails the script. That check does not describe the India plan.

## Leftovers

- The demo video is not recorded. The spoken script is in the README. Recording it is outside this run.
- nginx-proxy-manager is not on this machine. The reachable app is `127.0.0.1:65525`. When the host service is present, it forwards to that port with scheme `http` and websockets on, and it does not forward to 65524.
- GitHub Actions cannot be used as a check until the account billing limit is cleared. The local results are ruff, 86 pytest passes, the Compose launch, the end-to-end script, and the 100,000-row script.
- An earlier profile called the India salary page an O(limit) seek on `idx_emp_salary_usd`. `EXPLAIN QUERY PLAN` shows `idx_emp_status_country` and `USE TEMP B-TREE FOR ORDER BY`. The load log quoted above replaces that description. `logical-tests.log` is `RUFF_EXIT:0` and `86 passed in 7.33s`.
- UI states were confirmed in server-rendered HTML. A desktop browser did not click the pages.
- Unauthenticated `GET /` is rewritten to the login document so the 200 body contains `CompPulse` and `{"status":"ok"}`. Deep links still redirect to `/login`.
- A stale pay form redirects to `?conflict=1`. The action does not PATCH again. The visible sentence is `Record was modified. Reload and try again.`
- Search treats `-` as a word break before the existing FTS strip, so `Mary-Jane` is `Mary* AND Jane*` and a hyphenated query cannot be read as an FTS column filter.
- Next product work waits on a decision after this report.
