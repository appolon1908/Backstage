#!/usr/bin/env bash
set -Eeuo pipefail
readonly PUBLIC_DOCKER_CONFIG=/var/lib/codestra/docker-public
install -d -m 0700 "$PUBLIC_DOCKER_CONFIG"
if [[ ! -f "$PUBLIC_DOCKER_CONFIG/config.json" ]]; then
  printf '%s\n' '{"auths":{}}' > "$PUBLIC_DOCKER_CONFIG/config.json"
  chmod 0600 "$PUBLIC_DOCKER_CONFIG/config.json"
fi
export DOCKER_CONFIG="$PUBLIC_DOCKER_CONFIG"
cd "$(dirname "$0")/.."
readonly BACKSTAGE_BIND_IP="${BACKSTAGE_BIND_IP:-10.0.0.218}"
if ! ip -4 -o addr show | grep -Fq "inet ${BACKSTAGE_BIND_IP}/"; then
  echo "REFUSING: this Backstage deployment is restricted to the approved home server IP ${BACKSTAGE_BIND_IP}" >&2
  exit 1
fi
if grep -Eq "dangerouslyAllowOutsideDevelopment:[[:space:]]*true" app-config.production.yaml; then
  echo "REFUSING: guest authentication is not allowed on the home production instance" >&2
  exit 1
fi
if [[ "${BACKSTAGE_PRIVATE_STAGING_AUTH_APPROVED:-NO}" != "YES" ]]; then
  echo "REFUSING: private ingress authentication must be verified before starting Backstage" >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 32)" > .env
fi
docker compose config -q
docker compose pull
docker compose up -d
for _ in $(seq 1 30); do
  curl -fsS "http://${BACKSTAGE_BIND_IP}:17007/" >/dev/null && exit 0
  sleep 5
done
docker compose ps
docker compose logs --tail=100 backstage
exit 1
