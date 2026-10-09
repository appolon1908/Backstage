# Codestra Backstage

Repository-managed Backstage service catalog for Ralph Appolon's platform.

## Runtime

- Production target: local home application host `server-3` at `10.0.0.218` (no Hetzner usage).
- Edge ingress: `s1-middleware` at `10.0.0.73` (Caddy, private-only until approved).
- Deployment guide: [Home server topology and security gates](docs/HOME_SERVER_DEPLOYMENT.md).
- Backstage: v1.54.6 image pinned by digest
- Planned authenticated URL: `https://backstage.codestra.co` — NOT LIVE until private DNS, TLS, and authentication are certified.
- Private backend listener: `http://10.0.0.218:17007` (allow only `10.0.0.73` via server-3 firewall). Owner-controlled staging/production promotion remains disabled until identity certification.
- Database: dedicated PostgreSQL
- Public ingress is **not activated**. Only a proposed private Caddy Basic Auth template is provided; guest login has been disabled in production app config until approved Keycloak OIDC is implemented and certified.
- Any interim Basic Auth credentials belong in a protected Caddy service environment on `s1-middleware`; never commit or duplicate them.

Run `sudo ./scripts/deploy.sh` on the target host. Application secrets are generated into `.env` and are never committed.


## Mission Control

- Dashboard source: https://github.com/appolon1908/Backstage/tree/main/mission-control
- Linear execution lane: https://linear.app/passion-fruit/issue/PAS-196/mc-09-live-mission-control-dashboard-and-portfolio-status-surface
- Notion operations page: https://app.notion.com/p/3e27518c3e06810ab49df91aa1852940?pvs=204
- Appolon local dashboard: `C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\dashboard.html`

The dashboard joins GitHub, Linear, Notion, Appolon local Git, SentinelX, Prometheus, Alertmanager and Grafana. Runtime alerts remain fail-closed and are shown above repository status.


### Local dashboard API/UI integration (2026-10-08)

The interactive dashboard and its loopback API share one same-origin server. See [API/UI contract](mission-control/docs/API-UI-CONTRACT.md) for endpoint coverage, accessibility flow, local-only action controls, stale-data handling, and certification boundaries. Public Backstage is read-only until OIDC/API-gateway authorization is independently certified.
