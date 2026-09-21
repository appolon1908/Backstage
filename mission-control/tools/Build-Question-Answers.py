import os,json,datetime
BASE=r"C:\Users\Usuario\01_DEVELOPMENT\Mission-Control"
SNAP=os.path.join(BASE,"snapshot.json")
LOCAL=os.path.join(BASE,"local_work_status.json")
with open(SNAP,encoding="utf-8-sig") as f:s=json.load(f)
try:
    with open(LOCAL,encoding="utf-8-sig") as f:l=json.load(f)
except: l={"rows":[],"summary":{}}
repos=s.get("repositories",[])
summ=s.get("summary",{})
alerts=s.get("alerts",[])
now=datetime.datetime.now(datetime.timezone.utc)

def dt(v):
    if not v:return None
    try:return datetime.datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(datetime.timezone.utc)
    except:return None

dirty_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("dirty") or 0)>0 and x.get("repo")})
push_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("ahead") or 0)>0 and x.get("repo")})
behind_names=sorted({x.get("repo") for x in l.get("rows",[]) if int(x.get("behind") or 0)>0 and x.get("repo")})
stale=[]
for x in l.get("rows",[]):
    if not x.get("pending"):continue
    evidence=x.get("dirtySince") or x.get("unpushedSince")
    d=dt(evidence)
    if d and (now-d).total_seconds()>=86400:
        stale.append({"repo":x.get("repo"),"path":x.get("path"),"state":x.get("state"),"since":evidence})
blocked_names=sorted({r.get("name") for r in repos if r.get("blocked") and r.get("name")})
unassigned=sorted({r.get("name") for r in repos if r.get("linearIssue") and (not r.get("assignee") or r.get("assignee")=="Unassigned")})
remote_only=sorted({r.get("name") for r in repos if (r.get("localWork") or {}).get("state")=="Remote only"})
unlinked=sorted({r.get("name") for r in repos if r.get("linearStatus")=="Unlinked"})
today=now.date()
commits_today=0
for x in l.get("rows",[]):
    d=dt(x.get("lastCommitAt"))
    if d and d.date()==today:commits_today+=1

questions=[
 {"question":"What needs my attention right now?","status":"red" if (summ.get("criticalAlerts",0) or summ.get("blockedIssues",0) or summ.get("localPendingPush",0) or summ.get("localPendingCommit",0)) else "green",
  "answer":f'{summ.get("criticalAlerts",0)} critical alerts; {summ.get("blockedIssues",0)} blocked/conflict mission signals; {summ.get("localPendingCommit",0)} pending-commit worktrees; {summ.get("localPendingPush",0)} pending-push worktrees.'},
 {"question":"What is everyone working on?","status":"yellow","answer":f'{summ.get("inProgress",0)} Linear issues are In Progress and {summ.get("inReview",0)} are In Review. Repository rows show the linked mission and assignee where available.'},
 {"question":"What was completed today?","status":"gray","answer":f'Portfolio-wide completion is not proven by the current static snapshot. {commits_today} local worktree commit(s) are dated today, but a commit or review does not prove task completion. The Daily automation verifies completions from Linear/GitHub/CI evidence.'},
 {"question":"What is blocked?","status":"red" if blocked_names else "green","answer":(', '.join(blocked_names) if blocked_names else 'No repository blocker signals are currently linked')+f'. Total blocked/conflict/stuck issue signals: {summ.get("blockedIssues",0)}.'},
 {"question":"Which PRs have conflicts?","status":"gray","answer":"Unknown / Not Proven in this static snapshot. Open PRs are listed per repository, but a PR is only labeled conflicted after a remote GitHub mergeability check. The hourly cloud watch performs that check and must not infer conflict from review status."},
 {"question":"Which repos are dirty locally?","status":"orange" if dirty_names else "green","answer":(', '.join(dirty_names) if dirty_names else 'None')+f'. {summ.get("localPendingCommit",0)} worktree(s) currently have uncommitted changes.'},
 {"question":"What should happen next?","status":"red" if (blocked_names or summ.get("criticalAlerts",0) or push_names) else "blue","answer":f'First clear critical runtime/blocker evidence ({summ.get("criticalAlerts",0)} critical alert(s); blocked repos: {", ".join(blocked_names) or "none"}), then reconcile {summ.get("localPendingPush",0)} committed-but-unpushed worktree(s). The next implementation mission remains the linked Linear successor, not a review-only item.'},
 {"question":"Are production systems healthy?","status":"red" if summ.get("criticalAlerts",0) else "green","answer":f'No — not fully healthy.' if summ.get("criticalAlerts",0) else 'Yes — no critical Alertmanager alerts in the current snapshot.'},
 {"question":"Is staging ready?","status":"red","answer":"NO / NOT READY based on the current PAS-151 control-plane record. A review or successful local test does not change staging readiness until the governed staging certificate and runtime evidence pass."},
 {"question":"Is production ready?","status":"red","answer":f'NO GO while staging is not ready and {summ.get("criticalAlerts",0)} critical runtime alert(s) remain. Production readiness requires implementation, verification, rollback/recovery evidence, monitoring, and deployment/readback.'},
 {"question":"Who owns each task?","status":"blue","answer":f'Ownership is shown per repository from Linear. {len(unassigned)} linked repository mission(s) are currently unassigned in the dashboard mapping.'},
 {"question":"What changed since yesterday?","status":"gray","answer":"Unknown / Not Proven from the single current snapshot. The daily automation compares the new state with the previous daily state and reports commits, pushes, PR/CI changes, mission movement and alert changes."},
 {"question":"What has not moved?","status":"orange" if stale else "green","answer":f'{len(stale)} pending local worktree(s) have dirty/unpushed evidence older than 24 hours. '+(', '.join(sorted({x["repo"] for x in stale})) if stale else 'No >24h local pending evidence detected.')},
 {"question":"Did an agent finish without receiving the next task?","status":"gray","answer":"Unknown / Not Proven from this snapshot alone. The hourly watch treats a completed mission with no successor as an actionable incomplete handoff and sends a notification."},
 {"question":"Where is the evidence?","status":"blue","answer":"Each repository row links to GitHub, PRs, CI, Linear and Notion. Runtime evidence comes from Prometheus/Alertmanager/Grafana; local evidence comes from the Appolon 15-minute worktree scan."},
 {"question":"Which information is unknown or unverified?","status":"gray","answer":f'{len(remote_only)} repo(s) are Remote only locally; {len(unlinked)} repo(s) have no linked Linear mission. PR conflict state, completion-today and successor gaps remain unknown until their dedicated remote/history checks run.'}
]
s["questionAnswers"]=questions
s["readiness"]={"staging":{"state":"NOT READY","source":"PAS-151 current control-plane record"},"production":{"state":"NO GO","source":"staging not ready + critical runtime alerts"}}
s.setdefault("summary",{})["staleLocalPending24h"]=len(stale)
s["summary"]["remoteOnlyRepos"]=len(remote_only)
s["summary"]["unlinkedRepos"]=len(unlinked)
with open(SNAP,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)
print(json.dumps({"questions":len(questions),"stale":len(stale),"dirtyRepos":dirty_names,"pendingPushRepos":push_names,"blockedRepos":blocked_names,"remoteOnly":len(remote_only),"unlinked":len(unlinked)},separators=(",",":")))
