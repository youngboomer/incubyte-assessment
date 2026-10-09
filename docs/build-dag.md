# Build DAG

Frontend is hosted on `127.0.0.1:65525` for the nginx-proxy-manager host service. It is on networks `edge` and `internal`. Backend listens on port **65524**, is only on `internal`, and is not published to the host. `BACKEND_URL=http://backend:65524`. Compose does not start a proxy container.

Edges mean “must be merged before the child starts.” Nodes in the same level touch different directories and run in parallel.

```text
spec (docs/specs)
 ├─► backend-foundation ─┬─► directory-api ──► employees-ui ─┐
 │                       ├─► analytics-api ──► dashboard-ui ─┤
 │                       ├─► compensation-api ► profile-ui ──┼─► integration
 │                       └─► seed ──────────────────────────┘
 └─► frontend-foundation ─┴─► web-shell ────────────────────┘
```

| Level | Nodes | Parallel |
| --- | --- | --- |
| 0 | backend-foundation, frontend-foundation | yes |
| 1 | directory-api, analytics-api, compensation-api, seed, web-shell | yes, after level 0 |
| 2 | employees-ui, dashboard-ui, profile-ui | yes, after each node’s parents |
| 3 | integration | after level 2 and seed |

| Node | Prompt | Owns |
| --- | --- | --- |
| backend-foundation | `docs/prompts/00-foundation.md` | `backend/` |
| frontend-foundation | `docs/prompts/00-foundation.md` | `web/` |
| directory-api | `docs/prompts/01-directory.md` | employee read routes |
| analytics-api | `docs/prompts/02-analytics.md` | overview route |
| compensation-api | `docs/prompts/03-compensation.md` | pay, audit, FX |
| seed | `docs/prompts/04-seed.md` | `app/seed.py` |
| web-shell | `docs/prompts/05-web-shell.md` | login and shell |
| employees-ui | `docs/prompts/06-employees-ui.md` | `/employees` |
| dashboard-ui | `docs/prompts/07-dashboard-ui.md` | `/` |
| profile-ui | `docs/prompts/08-profile-ui.md` | profile and `/settings/fx` |
| integration | `docs/prompts/09-integration.md` | compose smoke and performance note |

`compose.yaml` is shared. Level-0 agents do not edit it. The orchestrator owns it. There is no proxy service in Compose.
