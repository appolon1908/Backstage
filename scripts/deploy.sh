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
if [[ ! -f .env ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 32)" > .env
fi
docker compose config -q
docker compose pull
docker compose up -d
for _ in $(seq 1 30); do
  curl -fsS http://10.40.0.4:17007/ >/dev/null && exit 0
  sleep 5
done
docker compose ps
docker compose logs --tail=100 backstage
exit 1
