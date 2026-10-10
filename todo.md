# Todo

## Combined change history

The Change history page shows pay changes only. `GET /audit` reads `compensation_audit_logs`, so detail edits and status changes (terminate, reactivate) are not in the global feed. They are only visible per employee, through `GET /employees/{id}/changes`.

The design for Change history shows one feed of both kinds. The page has a "Pay" tab and a disabled "Details" tab until this is done.

Open questions, to decide later:
- Backend: add a global `GET /changes` over `employee_change_logs`, mirroring `/audit`, or one combined endpoint that merges both tables by time.
- Cursor and ordering: `created_at` desc then `id` desc is not comparable across two tables, so a combined feed needs a shared sort key.
- Filters: person, department and date range should behave the same for both kinds.
- Frontend: replace the disabled "Details" tab, or merge into a single timeline.

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
