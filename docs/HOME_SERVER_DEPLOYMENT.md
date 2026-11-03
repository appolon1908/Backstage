# Codestra Backstage — home server cutover

**Hetzner is retired.** The Codestra deployment target is the connected local home-server fleet; the former `37.27.128.39` and `10.40.0.4` destinations are not authorized.

## Verified home network (October 8, 2026)

| Role | Connected server | LAN address | Authority |
|---|---|---|---|
| Backstage application | `server-3` / `crm` | `10.0.0.218` | Dedicated application container and PostgreSQL volume |
| Edge ingress | `s1-middleware` | `10.0.0.73` | Existing Caddy / TLS / request authentication |
| Monitoring | `s2-monitoring` | `10.0.0.220` | Prometheus, Grafana, Alertmanager |
| Development only | `dev-desktop` | `10.0.0.217` | Repository build / tests; not a production host |

At inspection, `server-3` had around 405 GB free filesystem capacity and 9 GB available memory; it already runs CRM/Odoo and other containers. Do not overwrite or restart unrelated services. Backstage is assigned port `10.0.0.218:17007` only; it is not bound to `0.0.0.0`.

## Deployment security gates

1. Merge the home-topology repository change through ordinary PR review and green CI. No direct push to protected main.
2. Establish a private Backstage container on `server-3` using the pinned image; keep its PostgreSQL database on the private Docker network and secrets in `.env` (owner-only, never commit).
3. Restrict the `server-3` inbound TCP port `17007` to `10.0.0.73` only (Caddy), with firewall readback; do **not** publicly forward `17007`.
4. Install the reviewed Caddy ingress template on `s1-middleware` **only after** supplying an operator-approved private Basic Auth hash or a tested Keycloak OIDC integration, validating Caddy and recording its prior config for rollback. The template permits home LAN/Tailscale ranges only and uses internal TLS; clients need the internal CA and split-DNS/hosts mapping to `10.0.0.73`.
5. The production Backstage app configuration intentionally disables guest auth. Configure a supported OIDC authentication provider and least-privilege client credentials before live promotion. The application should remain blocked, rather than turning on `dangerouslyAllowOutsideDevelopment`.
6. Check `GET /` and catalog readback from the LAN, negative tests for unauthenticated access and external IPs, catalog source authority, frontend controls, and rollback. A green source CI run is not a runtime certificate.

The `scripts/deploy.sh` entrypoint refuses a host whose address differs from `BACKSTAGE_BIND_IP` and requires `BACKSTAGE_PRIVATE_STAGING_AUTH_APPROVED=YES` after independent identity/ingress verification. That switch does not substitute for genuine authentication.

**DNS:** `backstage.codestra.co` still resolves to a retired public destination. Do not point GoDaddy records at the private address or an unverified home WAN IP. Public DNS changes require a separately approved secured ingress path, appropriate certificates, home-router firewall/forwarding or an approved tunnel, and verified user authentication. Until then use private LAN/VPN access only.

**Status:** Home topology implemented in source; live Backstage migration remains **NOT CERTIFIED** until authorized installation and end-to-end testing. Production GO=NO.

**Docker firewall warning:** Docker-published ports can bypass ordinary UFW input-chain rules. Confirm a Docker-aware `DOCKER-USER`/nftables policy or equivalent network ACL actually limits `10.0.0.218:17007` to ingress source `10.0.0.73`. Prove refusal from another LAN host before production approval. Do not assume UFW alone provides that restriction.
