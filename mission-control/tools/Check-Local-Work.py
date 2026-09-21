import os, re, json, subprocess, datetime, concurrent.futures
BASE=r"C:\Users\Usuario\01_DEVELOPMENT\Mission-Control"
SNAP=os.path.join(BASE,"snapshot.json")
OUT=os.path.join(BASE,"local_work_status.json")
RENDER=os.path.join(BASE,"Render-Dashboard.py")
REPOROOT=r"C:\Users\Usuario\01_DEVELOPMENT\GitHub\ingtrader21-spec"
DESKTOP=r"C:\Users\Usuario\Desktop"
WORKTREES=r"C:\Users\Usuario\01_DEVELOPMENT\Worktrees"

def run(path,args,timeout=8):
    try:
        r=subprocess.run(["git","-c","safe.directory=*","-C",path]+args,capture_output=True,text=True,timeout=timeout)
        return r.stdout.strip() if r.returncode==0 else ""
    except Exception:
        return ""

paths=set()
if os.path.isdir(REPOROOT):
    for n in os.listdir(REPOROOT):
        d=os.path.join(REPOROOT,n)
        if not os.path.isdir(d): continue
        for c in (d,os.path.join(d,"Code")):
            if os.path.exists(os.path.join(c,".git")):
                paths.add(os.path.normpath(c))
                wt=run(c,["worktree","list","--porcelain"],5)
                for line in wt.splitlines():
                    if line.startswith("worktree "):
                        p=line[9:].strip()
                        if os.path.exists(p): paths.add(os.path.normpath(p))
                break
for root in (DESKTOP,WORKTREES):
    if not os.path.isdir(root): continue
    for n in os.listdir(root):
        p=os.path.join(root,n)
        if not os.path.isdir(p): continue
        if os.path.exists(os.path.join(p,".git")): paths.add(os.path.normpath(p))
        if root==WORKTREES:
            try:
                for n2 in os.listdir(p):
                    p2=os.path.join(p,n2)
                    if os.path.isdir(p2) and os.path.exists(os.path.join(p2,".git")):
                        paths.add(os.path.normpath(p2))
            except: pass

rx=re.compile(r"github\.com[:/]ingtrader21-spec/([^/]+?)(?:\.git)?$")
def scan(p):
    remote=run(p,["remote","get-url","origin"],5)
    m=rx.search(remote)
    if not m:return None
    repo=re.sub(r"\.git$","",m.group(1))
    head=run(p,["rev-parse","--short","HEAD"],5)
    branch=run(p,["rev-parse","--abbrev-ref","HEAD"],5)
    upstream=run(p,["rev-parse","--abbrev-ref","--symbolic-full-name","@{u}"],5)
    try:
        st=subprocess.run(["git","-c","safe.directory=*","-C",p,"status","--porcelain=v1","-b"],capture_output=True,text=True,timeout=12)
        lines=st.stdout.splitlines() if st.returncode==0 else []
        scan_error="" if st.returncode==0 else "git status failed"
    except subprocess.TimeoutExpired:
        lines=[];scan_error="git status timed out"
    dirty=max(0,len(lines)-1)
    ahead=behind=0
    if upstream:
        cnt=run(p,["rev-list","--left-right","--count",f"{upstream}...HEAD"],6)
        mm=re.match(r"\s*(\d+)\s+(\d+)",cnt)
        if mm: behind,ahead=int(mm.group(1)),int(mm.group(2))
    elif lines:
        m1=re.search(r"ahead (\d+)",lines[0]);m2=re.search(r"behind (\d+)",lines[0])
        if m1:ahead=int(m1.group(1))
        if m2:behind=int(m2.group(1))
    last_at=run(p,["log","-1","--format=%cI"],5)
    last=run(p,["log","-1","--format=%h|%s"],5)
    unpushed=""
    if ahead>0 and upstream:
        logs=run(p,["log","--reverse","--format=%cI",f"{upstream}..HEAD"],6).splitlines()
        if logs:unpushed=logs[0]
    dirty_since=""
    if dirty>0:
        names=set()
        for args in (["diff","--name-only"],["diff","--cached","--name-only"],["ls-files","--others","--exclude-standard"]):
            names.update(x for x in run(p,args,6).splitlines() if x)
        ds=[]
        for rel in names:
            fp=os.path.join(p,rel)
            try: ds.append(datetime.datetime.fromtimestamp(os.path.getmtime(fp),datetime.timezone.utc).isoformat())
            except: pass
        if ds:dirty_since=min(ds)
    if scan_error:
        state,color,pending="Local scan needs review","orange",True
    elif not head:
        state,color,pending="Local shell / pending clone","gray",True
    elif dirty>0 and ahead>0:
        state,color,pending="WIP + unpushed","red",True
    elif dirty>0:
        state,color,pending="Started Local / pending commit","orange",True
    elif ahead>0:
        state,color,pending="Committed Local / pending push","red",True
    elif behind>0:
        state,color,pending="Pushed / local behind","orange",True
    else:
        state,color,pending="Pushed / synced","green",False
    started=dirty_since or unpushed or last_at
    return dict(repo=repo,path=p,branch=branch,head=head,upstream=upstream,dirty=dirty,ahead=ahead,behind=behind,
      state=state,color=color,pending=pending,startedAt=started,dirtySince=dirty_since,unpushedSince=unpushed,
      lastCommitAt=last_at,lastCommit=last,scanError=scan_error,upstreamEvidence="last-known local tracking ref")

rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for x in ex.map(scan,sorted(paths)):
        if x:rows.append(x)

now=datetime.datetime.now().astimezone().isoformat()
summary=dict(
    worktrees=len(rows),
    repos=len(set(x["repo"] for x in rows)),
    pendingCommit=sum(x["dirty"]>0 for x in rows),
    pendingPush=sum(x["ahead"]>0 for x in rows),
    behind=sum(x["behind"]>0 for x in rows),
    synced=sum(x["state"]=="Pushed / synced" for x in rows),
    scanNeedsReview=sum(bool(x["scanError"]) for x in rows),
)
doc={"checkedAt":now,"host":os.environ.get("COMPUTERNAME","Appolon"),"rows":sorted(rows,key=lambda x:(x["repo"].lower(),x["path"].lower())),"summary":summary}
with open(OUT,"w",encoding="utf-8") as f:json.dump(doc,f,indent=2)

try:
    with open(SNAP,encoding="utf-8-sig") as f:snap=json.load(f)
    by={}
    for x in rows:by.setdefault(x["repo"],[]).append(x)
    priority=["WIP + unpushed","Committed Local / pending push","Started Local / pending commit","Local scan needs review","Pushed / local behind","Local shell / pending clone","Pushed / synced"]
    for repo in snap.get("repositories",[]):
        items=by.get(repo.get("name"),[])
        if not items:
            repo["localWork"]={"state":"Remote only","color":"gray","pending":False,"checkedAt":now,"worktrees":0,"pendingCommit":0,"pendingPush":0,"behind":0,"startedAt":"","unpushedSince":"","dirtySince":"","latestCommitAt":""}
            continue
        chosen=next((x for st in priority for x in items if x["state"]==st),items[0])
        vals=lambda k:sorted([x[k] for x in items if x.get(k)])
        repo["localWork"]={"state":chosen["state"],"color":chosen["color"],"pending":any(x["pending"] for x in items),"checkedAt":now,"worktrees":len(items),
          "pendingCommit":sum(x["dirty"]>0 for x in items),"pendingPush":sum(x["ahead"]>0 for x in items),"behind":sum(x["behind"]>0 for x in items),
          "startedAt":(vals("startedAt") or [""])[0],"unpushedSince":(vals("unpushedSince") or [""])[0],"dirtySince":(vals("dirtySince") or [""])[0],
          "latestCommitAt":(sorted([x["lastCommitAt"] for x in items if x.get("lastCommitAt")],reverse=True) or [""])[0]}
    snap["localWorkCheckAt"]=now
    snap.setdefault("summary",{}).update(localPendingCommit=summary["pendingCommit"],localPendingPush=summary["pendingPush"],localBehind=summary["behind"],localSynced=summary["synced"],localScanNeedsReview=summary["scanNeedsReview"])
    with open(SNAP,"w",encoding="utf-8") as f:json.dump(snap,f,indent=2)
except Exception:
    pass
if os.path.exists(RENDER):
    try:subprocess.run(["python",RENDER],timeout=25)
    except:pass
print(json.dumps(doc,separators=(",",":")))
