# Mission Control Dashboard — Frontend / Backend Integration

## Implemented design flow

Executive → Repository Focus → Work Board (Table / Kanban / Timeline / My Work) → Runtime → Incomplete → Actions. The Refresh button reloads the current snapshot, and keyboard Enter/Space opens focused repository cards. External GitHub, Linear and Notion links are rendered only when the destination is a validated HTTPS URL.

This is an **evidence-first local operator UI**, not a production approval interface. A stale snapshot is explicitly marked stale, and no mission is marked Verified / Complete unless both the snapshot and verification-readback timestamps are fresh (within 24 hours).

## Same-origin backend endpoints

Run `python3 mission-control/tools/MissionControlServer.py` from this repo. The server defaults to `127.0.0.1:8765` and uses its own `mission-control` directory, on Linux and Windows. Customize only `MISSION_CONTROL_DASHBOARD_DIR` and `MISSION_CONTROL_DASHBOARD_PORT` for an isolated local instance.

| Method | Endpoint | Contract |
|---|---|---|
| GET | `/` | Serves the interactive `index.html` |
| GET | `/api/health` | Backend liveness and snapshot age/freshness |
| GET | `/api/snapshot` | Local read-model snapshot, not a live-data guarantee |
| GET | `/api/integrations` | Bounded read-only health probes for Mission Control API and Middleware API |
| GET | `/api/actions` | Local queued action readback |
| POST | `/api/action` | Validate and enqueue task/comment/stage request; does not directly change Linear |
| POST | `/api/action/{id}/cancel` | Cancel only a pending queued action |

Health checks default to loopback `http://127.0.0.1:8790/healthz` (Mission Control) and `http://127.0.0.1:8095/healthz` (Middleware). Operator-configured `MC_BACKEND_HEALTH_URL` and `MC_MIDDLEWARE_HEALTH_URL` must use HTTPS outside loopback. Unreachable backends are displayed as unavailable, never as green.

**Security:** the server binds to loopback, accepts JSON actions only with same-origin request headers and a trusted localhost Host header, validates repository names and exact Linear issue linkage, and refuses unproven Done transitions. It does not expose credentials or provide public write APIs. On public `backstage.codestra.co`, actions and drag-to-write controls remain read-only until an independently reviewed OIDC-enabled API gateway exists.

## Certification

`python3 -m unittest discover -s mission-control/tests -v` covers frontend routing and backend same-origin HTTP, health contract, task creation, queue readback, cancellation, wrong-issue rejection, untrusted Host, CORS/CSRF origin refusal, and evidence-gated Done rejection.

`node --check` on the inline script extracted from `index.html` validates JavaScript syntax. Optional real-browser smoke is gated with `CODESTRA_BROWSER_SMOKE=1`; do not claim it passed until a headless browser completes the suite. No production or provider effects are enabled by these tests.

### Not yet certified

The public Backstage deployment, actual authenticated Middleware API credentials and data endpoints, Keycloak OIDC policy, Caddy/Kong route wiring, fresh monitoring data, and full end-to-end browser interaction are **not covered** by the local contract tests. Preserve production NO GO until they have fresh independently verified evidence.

### Required interactive browser CI

The same-origin dashboard flow is exercised in a disposable local server and headless Chrome by `cd mission-control && npm ci --ignore-scripts && npm run test:browser`. The test verifies all six navigation views, four board views, keyboard navigation, fail-closed stale completion, queue/cancel readback, refresh, and mobile-width layout. It uses a one-repository synthetic fixture and never calls live Linear or provider endpoints. In developer environments with an already running Chrome DevTools server, set `CODESTRA_CDP_PORT` to reuse it without spawning a second Chrome instance. GitHub CI must run this as a required step, not silently skip it.
