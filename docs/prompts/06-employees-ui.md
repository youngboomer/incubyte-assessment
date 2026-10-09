# Employees UI

## Summary
Directory table with URL filters and a CSV download.

## Depends on
- Directory API merged
- Web shell merged

## Owns
- `/employees`
- Filter controls, keyset next/previous, CSV button

## Rules
- Filters live in the query string so a view can be shared
- Data loads in a Server Component. No browser fetch to FastAPI
- Format money by dividing the scaled string by `10^scale`, then `Intl.NumberFormat`
- Empty, loading, and error states are visible

## Done when
- Search, a filter, next page, and CSV use the current query
- Salary column is numeric order as returned by the API, not a client-side string sort
