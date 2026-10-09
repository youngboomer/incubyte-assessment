# Integration

## Summary
Prove the deploy topology and record measured performance.

## Owns
- README runbook, `docs/performance.md`, `docs/ai-usage.md`
- Compose smoke check

## Rules
- nginx-proxy-manager is the only published service in `compose.yaml`
- Frontend container can `GET http://backend:65524/health`
- Host port 65525 serves the frontend
- Host port 65524 is closed
- `scripts/check_perf.py` seeds 100,000 and records seed time, a filtered page, a deep keyset page, and the analytics query
- Demo credentials and the NPM proxy-host settings stay in the README
- Video script, about three minutes: find a person, explain USD vs local, change a salary, show the audit row, show a 409, read the dashboard

## Done when
- The smoke check matches the network in `docs/architecture.md`
- `docs/performance.md` contains numbers from a real run, not a target copied from the spec
