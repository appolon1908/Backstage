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
