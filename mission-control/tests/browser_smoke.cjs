/* Codestra Mission Control read-only/browser interaction smoke.
 * Starts a disposable loopback dashboard and (unless CODESTRA_CDP_PORT is set)
 * an isolated headless Chrome session. No external effects or credentials.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const net = require("node:net");
const cp = require("node:child_process");
const WebSocket = require("ws");

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const deadline = (predicate, ms, label) => (async () => {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    const value = await predicate();
    if (value) return value;
    await delay(100);
  }
  throw new Error("Timeout waiting for " + label);
})();
async function availablePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => server.listen(0, "127.0.0.1", resolve).once("error", reject));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}
async function httpResponse(url, method="GET") {
  const res = await fetch(url, { method, signal: AbortSignal.timeout(5000) });
  if (!res.ok) throw new Error(method + " " + url + ": HTTP " + res.status);
  const raw = await res.text();
  try { return JSON.parse(raw); } catch { return raw; }
}
async function attachTarget(browserPort) {
  const target = await httpResponse("http://127.0.0.1:" + browserPort + "/json/new?about:blank", "PUT");
  const ws = new WebSocket(target.webSocketDebuggerUrl, { handshakeTimeout: 5000 });
  await new Promise((resolve, reject) => { ws.once("open", resolve); ws.once("error", reject); });
  let nextId = 0;
  const pending = new Map();
  const exceptions = [];
  ws.on("message", data => {
    const msg = JSON.parse(data);
    if (msg.method === "Runtime.exceptionThrown") exceptions.push(msg.params?.exceptionDetails?.text ?? "exception");
    const item = pending.get(msg.id);
    if (!item) return;
    clearTimeout(item.timer);
    pending.delete(msg.id);
    msg.error ? item.reject(new Error(JSON.stringify(msg.error))) : item.resolve(msg.result);
  });
  function send(method, params={}) {
    return new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error("CDP timeout " + method)); }, 10000);
      pending.set(id, { timer, resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error("JS exception: " + JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  return { send, evaluate, exceptions, close: async () => {
    ws.close();
    try { await httpResponse("http://127.0.0.1:" + browserPort + "/json/close/" + target.id); } catch {}
  }};
}

async function main() {
  const root = path.resolve(__dirname, "..");
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "codestra-browser-"));
  const chromeProfile = path.join(scratch, "chrome");
  let serverProcess = null;
  let chromeProcess = null;
  let client = null;
  try {
    fs.copyFileSync(path.join(root, "index.html"), path.join(scratch, "index.html"));
    const fixture = {
      schemaVersion: 1,
      generatedAt: new Date().toISOString(),
      localWorkCheckAt: new Date().toISOString(),
      summary: { repositories: 1, inProgress: 1, criticalAlerts: 0 },
      repositories: [{
        name: "Middleware-", full: "appolon1908/Middleware-", group: "core",
        github: "https://github.com/appolon1908/Middleware-",
        linearUrl: "https://linear.app/passion-fruit/issue/PAS-447",
        linearIssue: "PAS-447", linearStatus: "In Progress", goal: "CI trust verification",
        assignee: "Agent 1", openPrs: 1, prs: [{
          number: 447, title: "Middleware CI", url: "https://github.com/appolon1908/Middleware-/pull/447"
        }]
      }],
      questionAnswers: [], readiness: { staging: { state: "NOT READY" }, production: { state: "NO GO" } },
      remoteRefresh: { checkedAt: "2026-09-25T00:00:00Z", missions: { "PAS-447": { complete: true } } }
    };
    fs.writeFileSync(path.join(scratch, "snapshot.json"), JSON.stringify(fixture));
    const port = await availablePort();
    serverProcess = cp.spawn(process.env.PYTHON || "python3",
      [path.join(root, "tools", "MissionControlServer.py")],
      { env: { ...process.env, MISSION_CONTROL_DASHBOARD_DIR: scratch,
               MISSION_CONTROL_DASHBOARD_PORT: String(port) }, stdio: "ignore" });
    await deadline(async () => {
      if (serverProcess.exitCode !== null) throw new Error("Dashboard server exited");
      try { return (await httpResponse("http://127.0.0.1:" + port + "/api/health")).ok; }
      catch { return false; }
    }, 8000, "dashboard server");
    let browserPort = Number(process.env.CODESTRA_CDP_PORT || 0);
    if (!browserPort) {
      const binary = process.env.CHROME_BIN || "google-chrome";
      chromeProcess = cp.spawn(binary, [
        "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-extensions",
        "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
        "--disable-background-networking", "--remote-debugging-port=0",
        "--user-data-dir=" + chromeProfile, "about:blank"
      ], { stdio: "ignore" });
      browserPort = await deadline(() => {
        if (chromeProcess.exitCode !== null) throw new Error("Chrome exited before CDP startup");
        const portfile = path.join(chromeProfile, "DevToolsActivePort");
        if (!fs.existsSync(portfile)) return 0;
        return Number(fs.readFileSync(portfile, "utf8").split("\n")[0]);
      }, 15000, "Chrome debugging port");
    }
    client = await attachTarget(browserPort);
    await client.send("Runtime.enable");
    await client.send("Page.enable");
    await client.send("Page.navigate", { url: "http://127.0.0.1:" + port + "/" });
    const ready = await client.evaluate("(async()=>{for(let i=0;i<100;i++){if(typeof REPOS!=='undefined'&&REPOS.length===1&&document.querySelectorAll('#kpis .card').length)return true;await new Promise(r=>setTimeout(r,100))}return false})()");
    assert.equal(ready, true, "UI must load API snapshot and render KPI cards");
    const results = await client.evaluate("(()=>{const result={};for(const v of ['executive','repo','pipeline','runtime','incomplete','actions']){document.querySelector('.navbtn[data-view=\"'+v+'\"]').click();result[v]=document.getElementById('view-'+v).classList.contains('active')}document.querySelector('.navbtn[data-view=\"executive\"]').click();const card=document.querySelector('.repo-card');card.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));result.cardKeyboard=document.getElementById('view-repo').classList.contains('active');document.querySelector('.navbtn[data-view=\"pipeline\"]').click();for(const v of ['table','kanban','timeline','mywork']){document.querySelector('.board-tab[data-boardview=\"'+v+'\"]').click();result['board_'+v]=document.getElementById('board-'+v).classList.contains('active')}result.doneNotFalselyVerified=truth(REPOS[0]).stage!=='done';return result})()");
    for (const [key, ok] of Object.entries(results)) assert.equal(ok, true, key + " did not respond");
    await client.evaluate("(()=>{document.querySelector('.navbtn[data-view=\"actions\"]').click();document.getElementById('taskRepo').value='Middleware-';document.getElementById('taskTitle').value='CI browser action';document.getElementById('taskBody').value='Cancelled automatically, no provider effects';document.getElementById('queueTaskBtn').click();return true})()");
    const queued = await deadline(async () => client.evaluate("!!document.querySelector('.cancel-action')"), 4000, "queued task action");
    assert.equal(queued, true);
    await client.evaluate("(()=>{document.querySelector('.cancel-action').click();return true})()");
    const cancelled = await deadline(async () => client.evaluate("!!document.querySelector('.status-cancelled')"), 4000, "canceled task");
    assert.equal(cancelled, true);
    const actions = await httpResponse("http://127.0.0.1:" + port + "/api/actions");
    assert.equal(actions.items.length, 1);
    assert.equal(actions.items[0].status, "cancelled");
    await client.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const mobile = await client.evaluate("({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth})");
    assert.equal(mobile.width, 390);
    assert.equal(mobile.overflow, false, "Mobile page should not scroll horizontally");
    await client.evaluate("(()=>{document.getElementById('refreshDashboard').click();return true})()");
    await deadline(async () => client.evaluate("document.getElementById('stamp').textContent.includes('Snapshot')"), 4000, "dashboard refresh");
    assert.deepEqual(client.exceptions, [], "No uncaught page exceptions");
    console.log("BROWSER_SMOKE=PASS: 6 views, 4 board views, keyboard focus, task enqueue/cancel, refresh, stale-gate, mobile layout");
  } finally {
    if (client) await client.close();
    if (serverProcess) serverProcess.kill("SIGTERM");
    if (chromeProcess) chromeProcess.kill("SIGTERM");
    await delay(300);
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}
main().catch(error => { console.error("BROWSER_SMOKE=FAIL", error.stack || error); process.exitCode = 1; });
