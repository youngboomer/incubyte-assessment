# Profile and FX UI

## Summary
Edit pay, show the audit trail, and edit a planning rate.

## Depends on
- Compensation API merged
- Web shell merged

## Owns
- Employee profile (drawer or `/employees/[id]`)
- `/settings/fx`

## Rules
- Server Actions call FastAPI. The form sends `version_id`
- 409 is an inline message with a reload. The action does not retry the write
- Audit list is newest first and shows local pay, USD, rate, reason, and effective date
- The FX form states that saving recomputes USD for that currency and does not rewrite history

## Done when
- A successful save shows the new version
- A forced stale `version_id` shows the 409 state
- An FX save shows the updated rate
