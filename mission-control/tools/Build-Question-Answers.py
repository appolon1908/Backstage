import os,json,datetime
BASE=r"C:\Users\Usuario\01_DEVELOPMENT\Mission-Control"
SNAP=os.path.join(BASE,"snapshot.json")
LOCAL=os.path.join(BASE,"local_work_status.json")
REMOTE=os.path.join(BASE,"remote_refresh.json")
with open(SNAP,encoding="utf-8-sig") as f:s=json.load(f)
try:
    with open(LOCAL,encoding="utf-8-sig") as f:l=json.load(f)
except: l={"rows":[],"summary":{}}
try:
    with open(REMOTE,encoding="utf-8-sig") as f:r=json.load(f)
except: r={}
repos=s.get("repositories",[]); summ=s.get("summary",{}); now=datetime.datetime.now(datetime.timezone.utc)
def dt(v):
    if not v:return None
    try:return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(datetime.timezone.utc)
    except:return None
remote_at=dt(r.get("checkedAt")); remote_fresh=bool(remote_at and (now-remote_at).total_seconds()<7200)
dirty_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("dirty") or 0)>0 and x.get("repo")})
push_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("ahead") or 0)>0 and x.get("repo")})
behind_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("behind") or 0)>0 and x.get("repo")})
stale=[]
for x in l.get("rows",[]):
    if not x.get("pending"):continue
    d=dt(x.get("dirtySince") or x.get("unpushedSince"))
    if d and (now-d).total_seconds()>=86400:stale.append(x)
remote_only=sorted({x.get("name") for x in repos if (x.get("localWork") or {}).get("state")=="Remote only"})
unlinked=sorted({x.get("name") for x in repos if x.get("linearStatus")=="Unlinked"})
unassigned=sorted({x.get("name") for x in repos if x.get("linearIssue") and (not x.get("assignee") or x.get("assignee")=="Unassigned")})
commits_today=0
for x in l.get("rows",[]):
    d=dt(x.get("lastCommitAt"))
    if d and d.date()==now.date():commits_today+=1
# Apply fresh remote mission authority to the repository rows so review/implementation state is not hidden by stale mapping.
if remote_fresh:
    missions=r.get("missions") or {}
    mapping={"klyrow.com":("PAS-198" if missions.get("PAS-198") else "PAS-195"),"Keycloak":"PAS-194","Caddy":"PAS-151","Kong":"PAS-151","Middleware-":"PAS-151"}
    for repo in repos:
        mid=mapping.get(repo.get("name")); m=missions.get(mid) if mid else None
        if not m:continue
        repo["linearIssue"]=mid; repo["linearStatus"]=(m.get("status") or "").split(" /")[0]; repo["assignee"]=m.get("owner") or repo.get("assignee")
        repo["goal"]=m.get("title") or repo.get("goal"); repo["linearUrl"]=m.get("url") or repo.get("linearUrl")
        if not m.get("complete",False):
            repo["blocked"]=True; repo["blocker"]=(m.get("missing") or "Completion evidence missing")[:900]; repo["blockerUrl"]=m.get("url") or repo.get("blockerUrl")
    s["remoteRefresh"]=r; s["remoteRefreshAt"]=r.get("checkedAt")
    # Monitoring was re-read this run; keep snapshot values synchronized.
    mon=r.get("monitoring") or {}
    summ["activeAlerts"]=mon.get("activeAlerts",summ.get("activeAlerts",0)); summ["criticalAlerts"]=mon.get("criticalAlerts",summ.get("criticalAlerts",0))
blocked_names=sorted({x.get("name") for x in repos if x.get("blocked") and x.get("name")})
if remote_fresh:
    a=r.get("actionsCapacity") or {}; missions=r.get("missions") or {}; prs=r.get("prChecks") or []
    checked=', '.join([f'{p.get("repo","?").split("/")[-1]} #{p.get("number")}' for p in prs])
    nonmerge=[p for p in prs if p.get("mergeable") is False]
    conflicts=("Confirmed conflict: "+', '.join(f'{p.get("repo")} #{p.get("number")}' for p in nonmerge)) if nonmerge else f'No confirmed Git conflicts among the {len(prs)} active-mission PRs checked ({checked}); all checked PRs report mergeable=true. Portfolio-wide PR conflict state outside this set is Unknown / Not Proven.'
    p199=missions.get("PAS-199") or {}
    platform=r.get("platformProtocol") or {}
    protocol_children=platform.get("children") or []
    p214=missions.get("PAS-214") or {}
    p214_pr=next((p for p in prs if p.get("repo")=="ingtrader21-spec/klyrow.com" and p.get("number")==170),{})
    q=[
      {"question":"What needs my attention right now?","status":"red","answer":f'{summ.get("criticalAlerts",0)} critical runtime alerts. {a.get("issue","PAS-190")} remains the release-wide hosted-Actions blocker ({a.get("status","Unknown")}, {a.get("priority","Urgent")}). PAS-151 staging is NOT READY. PAS-214 is Implemented/In Review at klyrow.com PR #170 but not Verified/Complete because exact-head hosted CI is {p214_pr.get("ci","not proven")}, review is {p214_pr.get("review","not proven")}, and staging/readback/recovery evidence is missing. PAS-234 and PAS-235 are In Progress but remain Reviewed/Defined. Local: {summ.get("localPendingCommit",0)} pending-commit and {summ.get("localPendingPush",0)} pending-push worktrees.'},
      {"question":"What is everyone working on?","status":"yellow","answer":"PAS-214: Billing & Finance Gate B material implementation is in review at klyrow.com PR #170. PAS-151: partial implementation with staging certification incomplete. PAS-198: Webmail/Postal observability implementation in review. PAS-199: PRO-S1 Organization & Identity implementation in review at PR #167. PAS-234 Middleware and PAS-235 Caddy are In Progress for Gate A 01–05 only and remain Reviewed/Defined; PAS-236–243 remain Backlog/Reviewed-Defined. PAS-194/PAS-192 remain identity prerequisite/runtime lanes. PAS-190 remains the CI-capacity blocker."},
      {"question":"What was completed today?","status":"gray","answer":f'PAS-196 Mission Control is an evidence-backed completed control-plane task. PAS-214 has material implementation evidence but is not complete; exact-head hosted CI/review and required staging/runtime/recovery evidence are missing. No PAS-199 or PAS-233–243 lane is newly counted complete in this refresh. Portfolio-wide exact completed-today count remains Unknown / Not Proven. {commits_today} local worktree commit(s) are dated today, but commits alone are not completion.'},
      {"question":"What is blocked?","status":"red","answer":f'{a.get("issue","PAS-190")}: hosted Actions capacity/billing. PAS-214: exact-head hosted CI startup failure/zero jobs, no submitted review, PAS-190, and missing staging/readback/recovery proof. PAS-151: exact-head CI plus governed staging apply/full-chain readback. PAS-198: exact-head hosted CI, independent review and immutable staging validation. PAS-199: exact-head hosted CI, independent review, PAS-194 staging identity readiness and PAS-192 runtime identity certification. Runtime also has {summ.get("criticalAlerts",0)} critical alerts.'},
      {"question":"Which PRs have conflicts?","status":"red" if nonmerge else "green","answer":conflicts},
      {"question":"Which repos are dirty locally?","status":"orange" if dirty_names else "green","answer":(', '.join(dirty_names) if dirty_names else 'None')+f'. {summ.get("localPendingCommit",0)} worktree(s) have uncommitted changes; {summ.get("localPendingPush",0)} worktree(s) have local commits pending push; {summ.get("localBehind",0)} worktree(s) are behind. Behind repos: '+(', '.join(behind_names) if behind_names else 'None')+'. Local evidence is not remote verification.'},
      {"question":"What should happen next?","status":"red","answer":f'Clear {a.get("issue","PAS-190")} without weakening gates. Then rerun exact-head hosted CI for PR #170 and the other checked active PRs, obtain independent review, and complete immutable/governed staging validation and required readback/rollback. PAS-214 must remain In Review until those gates pass. PAS-234 and PAS-235 may continue Gate A 01–05 only and must not be classified Implemented without material change evidence.'},
      {"question":"Are production systems healthy?","status":"red","answer":f'No. Prometheus scrape health is Codestra {r.get("monitoring",{}).get("codestraPrometheus","Unknown")}, Klyrow {r.get("monitoring",{}).get("klyrowPrometheus","Unknown")}, Telnexa {r.get("monitoring",{}).get("telnexaPrometheus","Unknown")}; Grafana health is reported OK, but Alertmanager still has {summ.get("activeAlerts",0)} active / {summ.get("criticalAlerts",0)} critical alerts.'},
      {"question":"Is staging ready?","status":"red","answer":"NO / NOT READY. PAS-151 has source/rehearsal evidence, but hosted exact-head CI is not executing real steps, canonical staging apply is incomplete, the Middleware application plane is not certified running, and full Caddy→Kong→Middleware readback/rollback is missing. PAS-214 also lacks exact-head hosted CI/review and staging/readback/recovery proof."},
      {"question":"Is production ready?","status":"red","answer":f'NO GO. Staging is not ready, required hosted CI is blocked, and {summ.get("criticalAlerts",0)} critical runtime alerts remain. PR #170 source/local test evidence does not authorize production or live charging.'},
      {"question":"Who owns each task?","status":"blue","answer":f'{a.get("owner","Unknown")} owns the checked release blocker and current PAS-151/PAS-198/PAS-199/PAS-214/PAS-194/PAS-192/PAS-233/PAS-234/PAS-235 records. Linear remains authoritative for every mission assignee, priority, due date, blocker and execution stage; dashboard and Notion summaries follow it.'},
      {"question":"What changed since yesterday?","status":"yellow","answer":f'klyrow.com PR #170 added material PRO-S3.B Billing & Finance Gate B implementation at exact head {p214_pr.get("head","unknown")} and PAS-214 is In Review / Implemented. Its exact-head CI is {p214_pr.get("ci","not proven")} and review is {p214_pr.get("review","not proven")}, so it is not Complete. PAS-235 moved Backlog → In Progress but remains Reviewed/Defined. Appolon local truth is {summ.get("localPendingCommit",0)} pending-commit, {summ.get("localPendingPush",0)} pending-push, {summ.get("localBehind",0)} behind and {summ.get("localSynced",0)} synced worktrees. Runtime remains {summ.get("activeAlerts",0)} active / {summ.get("criticalAlerts",0)} critical with all monitored Prometheus targets up.'},
      {"question":"What has not moved?","status":"orange","answer":f'PAS-190 remains urgent but {a.get("status","Unknown")} while blocking exact-head acceptance. PAS-214 remains In Review until hosted exact-head CI, review and required staging/readback/recovery evidence pass. PAS-236–243 remain Backlog/Reviewed-Defined. PAS-234 and PAS-235 have started Gate A but still have no mission-specific material implementation/completion proof. {len(stale)} pending local worktree(s) have dirty/unpushed evidence older than 24 hours.'},
      {"question":"Did an agent finish without receiving the next task?","status":"yellow","answer":"No finished-without-successor gap is proven in the checked lanes. PAS-214 has explicit remaining verification/certification work; PAS-234 and PAS-235 each have Gate A next tasks, and PAS-236–243 remain defined portfolio successors. Starting, assigning or reviewing a mission is not implementation or completion."},
      {"question":"Where is the evidence?","status":"blue","answer":"GitHub supplies exact-head PR/workflow evidence, including klyrow PR #170 and its zero-job startup failure; Linear supplies PAS-214 and platform-lane execution truth; SentinelX supplies the fresh Appolon worktree scan; Prometheus/Alertmanager/Grafana supply runtime truth; Notion is the durable architecture/handoff record. The dashboard is a derived read model and governed action surface."},
      {"question":"Which information is unknown or unverified?","status":"gray","answer":f'Portfolio-wide completed-today count and PR conflict state outside the {len(prs)} checked active PRs remain Unknown / Not Proven. PAS-214 exact-head hosted CI/review and staging/readback/recovery are unverified. PAS-234/PAS-235 implementation is not proven and PAS-236–243 remain definition-only. PAS-199 runtime identity completion is unverified pending PAS-194/PAS-192. Exact local Render-Dashboard.py byte parity with Backstage remains drift even though required V2 behavior and localhost health are green. {len(remote_only)} repo(s) are Remote only and {len(unlinked)} repo(s) are unlinked in the snapshot.'}
    ]
else:
    q=[
      {"question":"What needs my attention right now?","status":"red" if (summ.get("criticalAlerts",0) or summ.get("blockedIssues",0) or summ.get("localPendingPush",0) or summ.get("localPendingCommit",0)) else "green","answer":f'{summ.get("criticalAlerts",0)} critical alerts; {summ.get("blockedIssues",0)} blocked/conflict mission signals; {summ.get("localPendingCommit",0)} pending-commit worktrees; {summ.get("localPendingPush",0)} pending-push worktrees.'},
      {"question":"What is everyone working on?","status":"yellow","answer":f'{summ.get("inProgress",0)} Linear issues are In Progress and {summ.get("inReview",0)} are In Review. Remote mission refresh is stale/unavailable.'},
      {"question":"What was completed today?","status":"gray","answer":f'Unknown / Not Proven portfolio-wide. {commits_today} local worktree commit(s) are dated today, but commits/reviews do not prove completion.'},
      {"question":"What is blocked?","status":"red" if blocked_names else "green","answer":(', '.join(blocked_names) if blocked_names else 'No linked repository blockers')+f'. Snapshot blocked/conflict issue signals: {summ.get("blockedIssues",0)}.'},
      {"question":"Which PRs have conflicts?","status":"gray","answer":"Unknown / Not Proven — the remote GitHub mergeability refresh is stale or unavailable."},
      {"question":"Which repos are dirty locally?","status":"orange" if dirty_names else "green","answer":(', '.join(dirty_names) if dirty_names else 'None')+f'. {summ.get("localPendingCommit",0)} worktree(s) have uncommitted changes.'},
      {"question":"What should happen next?","status":"red","answer":"Refresh remote GitHub/Linear/Notion authority, then clear critical runtime blockers and local unpushed work without bypassing gates."},
      {"question":"Are production systems healthy?","status":"red" if summ.get("criticalAlerts",0) else "green","answer":"No — not fully healthy." if summ.get("criticalAlerts",0) else "No critical alerts in the current local snapshot."},
      {"question":"Is staging ready?","status":"red","answer":"NO / NOT READY based on PAS-151 until fresh remote/runtime certification proves otherwise."},
      {"question":"Is production ready?","status":"red","answer":f'NO GO while staging is not ready and {summ.get("criticalAlerts",0)} critical runtime alert(s) remain.'},
      {"question":"Who owns each task?","status":"blue","answer":f'Ownership is shown per repository from Linear. {len(unassigned)} linked repository mission(s) are unassigned.'},
      {"question":"What changed since yesterday?","status":"gray","answer":"Unknown / Not Proven — remote/history comparison is stale or unavailable."},
      {"question":"What has not moved?","status":"orange" if stale else "green","answer":f'{len(stale)} local pending worktree(s) have evidence older than 24 hours.'},
      {"question":"Did an agent finish without receiving the next task?","status":"gray","answer":"Unknown / Not Proven — successor graph check is stale or unavailable."},
      {"question":"Where is the evidence?","status":"blue","answer":"Local evidence is in SentinelX/Appolon worktree scan; remote GitHub/Linear/Notion evidence requires the cloud refresh."},
      {"question":"Which information is unknown or unverified?","status":"gray","answer":f'Remote refresh is stale/unavailable; PR conflicts, completed-today and successor gaps are Unknown / Not Proven. {len(remote_only)} repo(s) are Remote only; {len(unlinked)} repo(s) unlinked.'}
    ]
s["questionAnswers"]=q
s["readiness"]={"staging":{"state":"NOT READY","source":"PAS-151 current control-plane record"},"production":{"state":"NO GO","source":"staging not ready + critical runtime alerts"}}
s.setdefault("summary",{})["staleLocalPending24h"]=len(stale); s["summary"]["remoteOnlyRepos"]=len(remote_only); s["summary"]["unlinkedRepos"]=len(unlinked)
with open(SNAP,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)
qa_payload={
    "generatedAt":r.get("checkedAt") or s.get("generatedAt") or datetime.datetime.now().astimezone().isoformat(),
    "questionAnswers":q,
    "readiness":s.get("readiness",{}),
    "syncMetadata":r.get("syncMetadata") or {},
    "summary":{
        "activeAlerts":summ.get("activeAlerts",0),"criticalAlerts":summ.get("criticalAlerts",0),
        "localPendingCommit":summ.get("localPendingCommit",0),"localPendingPush":summ.get("localPendingPush",0),
        "localBehind":summ.get("localBehind",0),"localSynced":summ.get("localSynced",0),
        "localScanNeedsReview":summ.get("localScanNeedsReview",0),"staleLocalPending24h":len(stale)
    }
}
with open(os.path.join(BASE,"question_answers.json"),"w",encoding="utf-8") as f:json.dump(qa_payload,f,indent=2,ensure_ascii=False)
print(json.dumps({"questions":len(q),"remoteFresh":remote_fresh,"stale":len(stale),"dirtyRepos":dirty_names,"pendingPushRepos":push_names,"blockedRepos":blocked_names},separators=(",",":")))