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
from http.server import ThreadingHTTPServer
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


if __name__ == "__main__":
    unittest.main()
