# Web shell

## Summary
Login, layout, and a server-side client for FastAPI.

## Owns
- `/login`, app shell, nav, `BACKEND_URL` client, shared response types
- httpOnly cookie `comppulse_session`

## Does not touch
- Feature pages (directory, dashboard, profile, FX)
- Any browser call to the backend

## Rules
- Server code calls `BACKEND_URL` with the bearer token
- Do not add `NEXT_PUBLIC_API_URL` or publish port 8000
- 401 sends the user to `/login`
- Types match `docs/api-contract.md`. Do not rename fields

## Done when
- A logged-out visit to `/` redirects to `/login`
- A valid demo login reaches the shell, which can show the health status from the server fetch
