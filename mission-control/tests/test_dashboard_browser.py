from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

import test_dashboard_integration as integration_test


class _BodyAttributes(HTMLParser):
    attributes: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.attributes = dict(attrs)


@unittest.skipUnless(os.environ.get('CODESTRA_BROWSER_SMOKE') == '1',
                     'Optional browser smoke (set CODESTRA_BROWSER_SMOKE=1)')
class BrowserFlowTest(unittest.TestCase):
    """Real browser navigation and action lifecycle against an isolated server."""

    setUp = integration_test.DashboardAPITest.setUp

    def test_clickable_dashboard_browser_journey(self):
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        if chrome is None:
            self.skipTest("Headless Chrome is not installed on this runner")
        html = Path(self.directory, "index.html")
        marker = r"""
<script>
window.addEventListener('load',()=>{
  setTimeout(async()=>{
    const result={navigation:[],repoFocus:false,queued:false,cancelled:false,refresh:false,health:false};
    try{
      for(const view of ['executive','repo','pipeline','runtime','incomplete','actions']){
        const button=document.querySelector('.navbtn[data-view="'+view+'"]');
        button.click();
        result.navigation.push(document.getElementById('view-'+view).classList.contains('active'));
      }
      document.getElementById('taskRepo').value='Middleware-';
      document.getElementById('taskTitle').value='Browser smoke task';
      document.getElementById('queueTaskBtn').click();
      await new Promise(resolve=>setTimeout(resolve,400));
      result.queued=!!document.querySelector('.cancel-action');
      const cancel=document.querySelector('.cancel-action');
      if(cancel)cancel.click();
      await new Promise(resolve=>setTimeout(resolve,400));
      result.cancelled=!!document.querySelector('.status-cancelled');
      document.querySelector('.navbtn[data-view="executive"]').click();
      const card=document.querySelector('.repo-card');
      if(card)card.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
      result.repoFocus=document.getElementById('view-repo').classList.contains('active');
      document.getElementById('refreshDashboard').click();
      await new Promise(resolve=>setTimeout(resolve,400));
      result.refresh=!!document.getElementById('stamp').textContent.includes('Snapshot');
      result.health=!!document.getElementById('integrationStatus').textContent.includes('Backend APIs');
    }catch(error){result.error=String(error)}
    document.body.setAttribute('data-ci-smoke',JSON.stringify(result));
  },700);
});
</script>
"""
        html.write_text(html.read_text(encoding="utf-8").replace("</body>", marker + "</body>"),
                        encoding="utf-8")
        cmd = [
            chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--disable-extensions",
            "--virtual-time-budget=7500",
            "--user-data-dir=" + str(Path(self.directory, "chrome-profile")),
            "--dump-dom", f"http://127.0.0.1:{self.port}/",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        parser = _BodyAttributes()
        parser.feed(result.stdout)
        proof = parser.attributes.get("data-ci-smoke")
        self.assertIsNotNone(proof, result.stdout[-2000:])
        data = json.loads(proof)
        self.assertNotIn("error", data, data)
        self.assertEqual(data["navigation"], [True] * 6)
        for key in ("repoFocus", "queued", "cancelled", "refresh", "health"):
            self.assertTrue(data[key], (key, data))


if __name__ == "__main__":
    unittest.main()
