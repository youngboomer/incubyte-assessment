# Todo

## Single mixed history timeline

Change history has a Pay tab and a Details tab (detail and status changes). One mixed timeline that interleaves both by time is still possible: a combined endpoint over `compensation_audit_logs` and `employee_change_logs` with a shared sort key (`created_at`, then a per-table tiebreak).

## Future-dated termination

Terminating today flips the status to Terminated at once. The effective date is only saved in the change history, so a future date still removes the person from pay analytics immediately.

Wanted: an employee stays Active until the leaving date, then becomes Terminated.

Design notes, to confirm later:
- New `scheduled_terminations` table (employee, date, reason, who set it, applied or cancelled). No new column on `employees`, so existing databases need no migration.
- A past or today date still terminates now. A future date schedules instead.
- A small step applies due terminations: at startup, and at most once a minute on normal requests (there is no background scheduler). Applying one flips the status, bumps the version and writes the usual history row.
- Cancel or reschedule until the date arrives. Dates are UTC.
- Reject a pay change effective after a scheduled leaving date, with a plain message.
- Tests use an injectable clock, as the login limiter does.
- Screens: the Terminate button becomes "Schedule termination" for a future date; the profile shows "Leaving on 30 Jun 2026" with a Cancel link; the directory shows a small "Leaving 30 Jun" tag.
- Out of scope: "as of" views (for example pay overview as of a past date). Those need dated history for pay and status.
