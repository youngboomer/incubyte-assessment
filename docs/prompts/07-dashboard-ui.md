# Dashboard UI

## Summary
How ACME pays people: totals, quartiles, and charts.

## Depends on
- Analytics API merged
- Web shell merged

## Owns
- `/` dashboard inside the shell

## Rules
- One server fetch of `/analytics/overview`
- KPI strip, department bar, country bar, histogram, quartile strip
- USD formatting from scaled strings. Label planning rates as planning rates where a rate is shown
- Empty and error states

## Done when
- The page renders the overview payload, including a zero-count bucket
- Terminated employees are not added back on the client
