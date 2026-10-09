# CompPulse — Product Requirements

**User:** ACME’s HR manager. **Scale:** seed 10,000 employees; the design holds at 100,000.

## Goal

ACME keeps salary data for a multi-country workforce in spreadsheets. The HR manager needs one web application to look up a person, change their pay with a reason, and answer how the organization pays people. Figures used for comparison are converted to USD with a planning exchange rate, not a live market tick.

## In scope

- Directory with search, filters (country, department, currency, status), allow-listed sort, and keyset pages.
- Profile: local base and variable pay, USD equivalent, level, effective date.
- Pay change with a required reason and effective date. A stale edit is rejected and nothing is written.
- Append-only history of each change, including the USD amount and the planning rate at that moment.
- Dashboard for active employees: headcount, total and average USD pay, 25th / 50th / 75th percentiles, breakdown by department and country, USD histogram.
- Planning rates for eight countries, one currency each. Changing a rate recomputes stored USD for that currency. History rows stay as they were.
- Add an employee.
- CSV download of the current filtered directory. No spreadsheet import.
- One shared login, so a deployed URL is not a public salary list.

Countries: United States, United Kingdom, Germany, India, Singapore, Japan, Canada, Australia.

## Out of scope

| Left out | Why |
| --- | --- |
| Payroll, tax, paystubs, bank files | Statutory payroll is a different product. |
| Role matrix and multi-tenant isolation | The brief has one persona. |
| Live FX feeds | Planning uses a locked rate so yesterday’s answer stays restatable. |
| Spreadsheet import | A second writer recreates the problem being removed. |
| Revaluing history at today’s rate | The audit row stores the USD snapshot from the change. |
| Equity, bonus cycles, approval chains | Not required to answer how the org pays. |
| A person paid in a currency other than their country’s | One currency per country keeps the conversion explainable. |

Analytics default to active employees. Terminated people remain in the directory and in their history.
