# Codestra Backstage

Repository-managed Backstage service catalog for Ralph Appolon's platform.

## Runtime

- Target: 37.27.128.39 / private 10.40.0.4
- Backstage: v1.54.6 image pinned by digest
- Listener: http://10.40.0.4:17007
- Database: dedicated PostgreSQL
- Public exposure: disabled until DNS, TLS, and Keycloak OIDC are completed

Run `sudo ./scripts/deploy.sh` on the target host. Secrets are generated into `.env` and are never committed.
