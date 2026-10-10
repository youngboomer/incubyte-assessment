# Todo

## Combined change history

The Change history page shows pay changes only. `GET /audit` reads `compensation_audit_logs`, so detail edits and status changes (terminate, reactivate) are not in the global feed. They are only visible per employee, through `GET /employees/{id}/changes`.

The design for Change history shows one feed of both kinds. The page has a "Pay" tab and a disabled "Details" tab until this is done.

Open questions, to decide later:
- Backend: add a global `GET /changes` over `employee_change_logs`, mirroring `/audit`, or one combined endpoint that merges both tables by time.
- Cursor and ordering: `created_at` desc then `id` desc is not comparable across two tables, so a combined feed needs a shared sort key.
- Filters: person, department and date range should behave the same for both kinds.
- Frontend: replace the disabled "Details" tab, or merge into a single timeline.
