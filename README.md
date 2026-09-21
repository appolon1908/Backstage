# Codestra Backstage

Repository-managed Backstage service catalog for Ralph Appolon's platform.

## Runtime

- Target: 37.27.128.39 / private 10.40.0.4
- Backstage: v1.54.6 image pinned by digest
- Public URL: https://backstage.codestra.co
- Private listener: http://10.40.0.4:17007
- Database: dedicated PostgreSQL
- Public ingress is protected by Nginx Basic Auth until Keycloak OIDC replaces the guest provider.
- Basic Auth credentials are stored only on the target at `/etc/codestra/secrets/backstage-basic-auth.env`.

Run `sudo ./scripts/deploy.sh` on the target host. Application secrets are generated into `.env` and are never committed.


## Mission Control

- Dashboard source: https://github.com/appolon1908-hue/Backstage/tree/main/mission-control
- Linear execution lane: https://linear.app/passion-fruit/issue/PAS-196/mc-09-live-mission-control-dashboard-and-portfolio-status-surface
- Notion operations page: https://app.notion.com/p/3e27518c3e06810ab49df91aa1852940?pvs=204
- Appolon local dashboard: `C:\Users\Usuario\01_DEVELOPMENT\Mission-Control\dashboard.html`

The dashboard joins GitHub, Linear, Notion, Appolon local Git, SentinelX, Prometheus, Alertmanager and Grafana. Runtime alerts remain fail-closed and are shown above repository status.
