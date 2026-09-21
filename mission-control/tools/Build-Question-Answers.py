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
    mapping={"klyrow.com":"PAS-195","Keycloak":"PAS-194","Caddy":"PAS-151","Kong":"PAS-151","Middleware-":"PAS-151"}
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
    q=[
      {"question":"What needs my attention right now?","status":"red","answer":f'{summ.get("criticalAlerts",0)} critical runtime alerts. {a.get("issue","PAS-190")} is {a.get("priority","Urgent")} but {a.get("status","unknown")}; hosted Actions are capacity/billing-blocked. PAS-151 staging is NOT READY; PAS-195 is Implemented/In Review but exact-head CI is zero-step RED; PAS-194/PAS-192 remain blocked. Local: {summ.get("localPendingCommit",0)} pending-commit and {summ.get("localPendingPush",0)} pending-push worktrees.'},
      {"question":"What is everyone working on?","status":"yellow","answer":f'PAS-151: Implemented partially, staging certification incomplete. PAS-195: Implemented, In Review. PAS-194: Implemented prerequisite, blocked. PAS-192: Reviewed/Defined runtime certification, blocked. PAS-190: urgent CI-capacity restoration is assigned to {a.get("owner","Unknown")} but still {a.get("status","Unknown")}. Portfolio snapshot: {summ.get("inProgress",0)} In Progress, {summ.get("inReview",0)} In Review.'},
      {"question":"What was completed today?","status":"gray","answer":f'PAS-196 Mission Control is a verified completed control-plane task. Portfolio-wide exact completed-today count is Unknown / Not Proven in this refresh. PAS-151, PAS-195, PAS-194 and PAS-192 must NOT be counted complete. {commits_today} local worktree commits are dated today, but commits alone are not completion.'},
      {"question":"What is blocked?","status":"red","answer":f'{a.get("issue","PAS-190")}: hosted Actions capacity/billing. PAS-151: exact-head CI + governed staging apply/full-chain readback. PAS-195: exact-head hosted CI + independent approval. PAS-194: exact-head CI + live realm/DNS/TLS/test identities. PAS-192: blocked behind PAS-194. Runtime also has {summ.get("criticalAlerts",0)} critical alerts.'},
      {"question":"Which PRs have conflicts?","status":"red" if nonmerge else "green","answer":conflicts},
      {"question":"Which repos are dirty locally?","status":"orange" if dirty_names else "green","answer":(', '.join(dirty_names) if dirty_names else 'None')+f'. {summ.get("localPendingCommit",0)} worktree(s) have uncommitted changes. Keycloak also has a distinct local-only commit 4e76fa4 while remote PR #124 is at a49390e1; do not treat those SHAs as identical.'},
      {"question":"What should happen next?","status":"red","answer":f'Start/clear {a.get("issue","PAS-190")} first: {a.get("nextAction","restore hosted Actions execution")}. Then rerun exact-head CI for #165/#309/#124/#115/#116, obtain required independent reviews, and only then perform governed staging apply/readback. Do not restart the stale Middleware stack or bypass checks.'},
      {"question":"Are production systems healthy?","status":"red","answer":f'No. Prometheus scrape health is Codestra {r.get("monitoring",{}).get("codestraPrometheus","Unknown")}, Klyrow {r.get("monitoring",{}).get("klyrowPrometheus","Unknown")}, Telnexa {r.get("monitoring",{}).get("telnexaPrometheus","Unknown")}, but Alertmanager still has {summ.get("activeAlerts",0)} active / {summ.get("criticalAlerts",0)} critical alerts.'},
      {"question":"Is staging ready?","status":"red","answer":"NO / NOT READY. PAS-151 has new implementation/rehearsal evidence in Middleware #309 and mergeable Kong #115/#116, but exact-head hosted CI is not executing real steps, canonical staging reconciliation/apply is not complete, the current Middleware application plane is not certified running, and full Caddy→Kong→Middleware readback/rollback is missing."},
      {"question":"Is production ready?","status":"red","answer":f'NO GO. Staging is not ready, required hosted CI is blocked, and {summ.get("criticalAlerts",0)} critical runtime alerts remain. Source/local tests do not authorize production.'},
      {"question":"Who owns each task?","status":"blue","answer":f'{a.get("owner","Unknown")} owns PAS-190 and the current PAS-151/PAS-195/PAS-194/PAS-192 records. {len(unassigned)} linked repository mission(s) are unassigned in the dashboard mapping.'},
      {"question":"What changed since yesterday?","status":"yellow","answer":"Material current changes: PAS-190 root cause is confirmed as exhausted GitHub Actions minutes plus a billing problem; Middleware #309 added a bounded PAS-151 schema reconciler/rehearsal; klyrow #165 advanced to exact head 8295f7cc with isolated staging evidence but current hosted workflows are zero-step RED; Keycloak #124 remains mergeable but hosted checks are zero-step RED. Monitoring counts are unchanged."},
      {"question":"What has not moved?","status":"orange","answer":f'{len(stale)} pending local worktree(s) have dirty/unpushed evidence older than 24 hours ({", ".join(sorted({x.get("repo") for x in stale if x.get("repo")})) or "none"}). PAS-190 is urgent and assigned but still Todo/unstarted while it blocks multiple exact-head acceptance lanes.'},
      {"question":"Did an agent finish without receiving the next task?","status":"yellow","answer":f'No finished-without-successor case is proven in this refresh. However the required next blocker-clearing task is known: PAS-190 is assigned to {a.get("owner","Unknown")} but is still {a.get("status","Unknown")}, so successor execution has not started.'},
      {"question":"Where is the evidence?","status":"blue","answer":"GitHub exact-head PR metadata/workflow jobs were checked for klyrow #165, Middleware #309, Keycloak #124 and Kong #115/#116; Linear PAS-190/PAS-151/PAS-195/PAS-194/PAS-192 supplies mission/owner/status evidence; SentinelX supplies Appolon worktree and runtime monitoring evidence; Notion remains the architecture/handoff record."},
      {"question":"Which information is unknown or unverified?","status":"gray","answer":f'Portfolio-wide completed-today count, PR conflict state outside the {len(prs)} checked active PRs, exact alert onset ages, and completed-mission successor coverage outside the checked lanes remain Unknown / Not Proven. {len(remote_only)} repo(s) are Remote only on Appolon and {len(unlinked)} repo(s) have no linked Linear mission in the snapshot.'}
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
print(json.dumps({"questions":len(q),"remoteFresh":remote_fresh,"stale":len(stale),"dirtyRepos":dirty_names,"pendingPushRepos":push_names,"blockedRepos":blocked_names},separators=(",",":")))
