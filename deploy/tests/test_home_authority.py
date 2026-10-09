from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HomeServerDeploymentContract(unittest.TestCase):
    def text(self, file: str) -> str:
        return (ROOT / file).read_text(encoding="utf-8")

    def test_only_home_lan_binding(self):
        compose = self.text("docker-compose.yml")
        self.assertIn("${BACKSTAGE_BIND_IP:-10.0.0.218}:17007:7007", compose)
        self.assertNotIn("10.40.0.4", compose)
        self.assertNotIn("37.27.128.39", compose)
        self.assertIn("backstage_private", compose)
        self.assertIn("POSTGRES_PASSWORD", compose)
        self.assertIn("monitoring-catalog.yaml:/app/monitoring-catalog.yaml:ro", compose)

    def test_production_guest_disabled(self):
        config = self.text("app-config.production.yaml")
        self.assertIn("providers: {}", config)
        self.assertNotIn("dangerouslyAllowOutsideDevelopment: true", config)
        self.assertIn("target: /app/monitoring-catalog.yaml", config)
        self.assertNotIn("type: url\n      target: /app/monitoring-catalog.yaml", config)

    def test_deploy_requires_private_security_approval_and_correct_host(self):
        script = self.text("scripts/deploy.sh")
        self.assertIn("BACKSTAGE_PRIVATE_STAGING_AUTH_APPROVED", script)
        self.assertIn("BACKSTAGE_BIND_IP", script)
        self.assertIn('ip -4 -o addr show', script)
        self.assertNotIn("10.40.0.4", script)
        self.assertNotIn("37.27.128.39", script)

    def test_ingress_denies_outside_lan_and_requires_auth(self):
        caddy = self.text("deploy/backstage-home.caddy")
        self.assertIn("tls internal", caddy)
        self.assertIn("remote_ip 10.0.0.0/24 100.64.0.0/10", caddy)
        self.assertIn("basic_auth", caddy)
        self.assertIn("{$BACKSTAGE_BASIC_HASH}", caddy)
        self.assertIn("reverse_proxy 10.0.0.218:17007", caddy)
        self.assertIn("respond 403", caddy)
        self.assertNotIn("0.0.0.0:17007", caddy)


if __name__ == "__main__":
    unittest.main()
