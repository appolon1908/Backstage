from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "MissionControlServer.py"


class DashboardAPITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "snapshot.json").write_text(
            json.dumps({
                "schemaVersion": 1,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "repositories": [{"name": "Middleware-", "linearIssue": "PAS-447"}],
                "remoteRefresh": {"missions": {}},
            }), encoding="utf-8",
        )
        (self.directory / "index.html").write_text((ROOT / "index.html").read_text(), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("dashboard_server_under_test", SERVER)
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        previous_base = os.environ.get("MISSION_CONTROL_DASHBOARD_DIR")
        os.environ["MISSION_CONTROL_DASHBOARD_DIR"] = str(self.directory)
        try:
            spec.loader.exec_module(self.module)
        finally:
            if previous_base is None:
                os.environ.pop("MISSION_CONTROL_DASHBOARD_DIR", None)
            else:
                os.environ["MISSION_CONTROL_DASHBOARD_DIR"] = previous_base
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def request(self, path: str, body: object | None = None, headers=None):
        address = f"http://127.0.0.1:{self.port}{path}"
        kwargs = {"headers": headers or {}}
        if body is not None:
            kwargs["data"] = json.dumps(body).encode("utf-8")
            kwargs["headers"] = {"Content-Type": "application/json", **kwargs["headers"]}
            kwargs["method"] = "POST"
        try:
            with urllib.request.urlopen(urllib.request.Request(address, **kwargs), timeout=4) as response:
                raw = response.read()
                if response.headers.get("Content-Type", "").startswith("application/json"):
                    return response.status, json.loads(raw)
                return response.status, raw.decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_frontend_is_served_by_backend_at_root(self):
        status, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="refreshDashboard"', html)
        self.assertIn('id="integrationStatus"', html)
        self.assertIn('data-view="pipeline"', html)

    def test_snapshot_and_integration_health_are_machine_readable(self):
        status, data = self.request("/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(data["repositories"][0]["linearIssue"], "PAS-447")
        status, live = self.request("/api/integrations")
        self.assertEqual(status, 200)
        self.assertEqual({entry["name"] for entry in live["services"]},
                         {"mission-control-api", "middleware-api"})
        self.assertEqual(live["actions"], "local-only")
        self.assertTrue(live["snapshot"]["fresh"])

    def test_task_comment_stage_and_cancel_flow(self):
        status, invalid = self.request("/api/action", {"kind": "task", "repo": "Unknown", "title": "No"})
        self.assertEqual(status, 400)
        status, invalid = self.request("/api/action", {
            "kind": "comment", "repo": "Middleware-", "issueId": "PAS-999", "body": "wrong"
        })
        self.assertEqual(status, 400)
        status, locked = self.request("/api/action", {
            "kind": "stage", "repo": "Middleware-", "issueId": "PAS-447", "stage": "done"
        })
        self.assertEqual(status, 409)
        status, action = self.request("/api/action", {
            "kind": "task", "repo": "Middleware-", "title": "Review contracts",
            "body": "Read-only review", "priority": "High"
        })
        self.assertEqual(status, 201)
        action_id = action["action"]["id"]
        status, queue = self.request("/api/actions")
        self.assertEqual(status, 200)
        self.assertEqual(queue["items"][0]["id"], action_id)
        status, canceled = self.request(f"/api/action/{action_id}/cancel", {})
        self.assertEqual(status, 200)
        self.assertEqual(canceled["action"]["status"], "cancelled")
        status, queue = self.request("/api/actions")
        self.assertEqual(queue["items"][0]["status"], "cancelled")

    def test_untrusted_host_fails_closed(self):
        status, data = self.request("/api/action", {
            "kind": "task", "repo": "Middleware-", "title": "blocked"
        }, headers={"Host": "untrusted.example"})
        self.assertEqual(status, 403)
        self.assertEqual(data["error"], "untrusted Host")

    def test_cross_origin_actions_fail_closed(self):
        status, data = self.request("/api/action", {
            "kind": "task", "repo": "Middleware-", "title": "blocked"
        }, headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(data["error"], "cross-origin actions forbidden")



    def test_live_missions_require_private_server_side_auth(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MC_MISSIONS_TOKEN_FILE", None)
            status, result = self.request("/api/live/missions")
        self.assertEqual(status, 503)
        self.assertEqual(result["state"], "NOT_CONFIGURED")
        status, result = self.request("/api/live/missions", headers={"Host": "malicious.example"})
        self.assertEqual(status, 403)
        self.assertEqual(result["state"], "FORBIDDEN")

    def test_live_missions_proxy_only_authorized_loopback_upstream(self):
        token_file = self.directory / "mission-service-token"
        token_file.write_text("ephemeral-test-bearer", encoding="utf-8")
        token_file.chmod(0o600)

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_GET(self):
                redirect = getattr(self.server, "redirect_to", None)
                if redirect:
                    self.send_response(302)
                    self.send_header("Location", redirect)
                    self.end_headers()
                    return
                if self.headers.get("Authorization") != "Bearer ephemeral-test-bearer":
                    self.send_response(401)
                    self.end_headers()
                    return
                data = json.dumps({
                    "total": 1,
                    "items": [{"mission_id": "PAS-447", "product_goal": "CI trust review", "status": "IN_REVIEW"}],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        self.addCleanup(upstream.server_close)
        self.addCleanup(upstream.shutdown)
        env = {
            "MC_MISSIONS_TOKEN_FILE": str(token_file),
            "MC_MISSIONS_API_URL": f"http://127.0.0.1:{upstream.server_address[1]}/api/v1/missions?limit=20",
        }
        with patch.dict(os.environ, env):
            status, data = self.request("/api/live/missions")
            self.assertEqual(status, 200)
            self.assertEqual(data["state"], "CONNECTED")
            self.assertEqual(data["items"][0]["mission_id"], "PAS-447")
            self.assertEqual(data["total"], 1)
            self.assertNotIn("ephemeral-test-bearer", json.dumps(data))

            redirected_tokens = []

            class RedirectTrap(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    return

                def do_GET(self):
                    redirected_tokens.append(self.headers.get("Authorization"))
                    self.send_response(200)
                    self.end_headers()

            trap = ThreadingHTTPServer(("127.0.0.1", 0), RedirectTrap)
            threading.Thread(target=trap.serve_forever, daemon=True).start()
            self.addCleanup(trap.server_close)
            self.addCleanup(trap.shutdown)
            upstream.redirect_to = f"http://127.0.0.1:{trap.server_address[1]}/secret-leak"
            status, data = self.request("/api/live/missions")
            self.assertEqual(status, 503)
            self.assertEqual(data["state"], "UNAVAILABLE")
            self.assertEqual(redirected_tokens, [], "Bearer token must never cross a redirect")
            upstream.redirect_to = None

            token_file.chmod(0o644)
            status, data = self.request("/api/live/missions")
            self.assertEqual(status, 503)
            self.assertEqual(data["state"], "NOT_CONFIGURED")
            token_file.chmod(0o600)

            with patch.dict(os.environ, {
                "MC_MISSIONS_API_URL": "http://169.254.169.254/latest/meta-data/"
            }):
                status, data = self.request("/api/live/missions")
                self.assertEqual(status, 503)
                self.assertEqual(data["state"], "NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
