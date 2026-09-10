# Public observability ingress

The public DNS names terminate TLS at the host Nginx service on `37.27.128.39`.

| Name | Upstream | Authentication |
|---|---|---|
| `backstage.codestra.co` | `http://10.40.0.4:17007` | Nginx Basic Auth plus Backstage guest session |
| `sentry.codestra.co` | `http://10.40.0.4:19000` | Sentry account login |
| `wazuh.codestra.co` | `https://10.40.0.4:15601` | Wazuh dashboard login |

The Wazuh manager API, indexer, and agent ports are not exposed by this ingress. They remain private on the Hetzner vSwitch.

The GoDaddy record manifest is `deploy/dns-observability.csv`. The Nginx pre-certificate configuration is `deploy/nginx-observability.conf`. Certbot manages the live TLS directives and renewal schedule on the server.

Generated Backstage Basic Auth credentials are stored only at `/etc/codestra/secrets/backstage-basic-auth.env` with mode 0600. Replace the temporary outer Basic Auth layer with Keycloak OIDC before enabling direct Backstage guest access.
