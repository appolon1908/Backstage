import os, json, html
BASE=r"C:\Users\Usuario\01_DEVELOPMENT\Mission-Control"
SNAP=os.path.join(BASE,"snapshot.json")
OUT=os.path.join(BASE,"dashboard.html")
with open(SNAP,encoding="utf-8-sig") as f:s=json.load(f)
repos=s.get("repositories",[])
summ=s.get("summary",{})
alerts=s.get("alerts",[])
mon=s.get("monitoring",{})
prom=(mon.get("codestra") or {}).get("prometheus") or {}
am=(mon.get("codestra") or {}).get("alertmanager") or {}
kp=(mon.get("klyrow") or {}).get("prometheus") or {}
tp=(mon.get("telnexa") or {}).get("prometheus") or {}

def e(v):return html.escape(str(v if v is not None else ""),quote=True)
def active_mission(r):
    return bool(r.get("linearIssue")) and r.get("linearStatus") not in ("Unlinked","Duplicate","Canceled","Cancelled")
def implementation_signal(r):
    w=r.get("localWork") or {}
    return bool((r.get("dirtyFiles") or 0)>0 or (r.get("maxAhead") or 0)>0 or (r.get("openPrs") or 0)>0 or (w.get("pendingCommit") or 0)>0 or (w.get("pendingPush") or 0)>0)
def completion_truth(r):
    if not active_mission(r):
        return ("No active mission","gray","No active Linear execution mission is linked.")
    status=r.get("linearStatus") or ""
    impl=implementation_signal(r)
    if status=="Done":
        if impl:
            return ("Done status / verification not proven","yellow","Linear is Done and code-change evidence exists, but tests/CI/runtime completion must still be proven.")
        return ("Done status / implementation not proven","red","Linear is Done, but this snapshot does not prove implementation. Review/definition alone is not completion.")
    if status=="In Review":
        if impl:
            return ("Review + implementation evidence","yellow","Review is in progress and code-change evidence exists; verification/completion is still pending.")
        return ("Review only / implementation not proven","red","Review/definition exists, but no implementation evidence is proven in this snapshot.")
    if impl:
        return ("Implementation in progress","orange","Local/PR code-change evidence exists; verification and completion remain pending.")
    return ("Defined / implementation not proven","red","A mission is defined, but implementation evidence is not proven.")

truths={r.get("name"):completion_truth(r) for r in repos}
incomplete=sum(1 for r in repos if active_mission(r) and truths[r.get("name")][0] not in ("No active mission",))
review_only=sum(1 for r in repos if truths[r.get("name")][0] in ("Review only / implementation not proven","Defined / implementation not proven","Done status / implementation not proven"))

css="""*{box-sizing:border-box}body{margin:0;font:14px/1.45 Inter,system-ui;background:#071018;color:#e9f2f8}a{color:#8fc6ff;text-decoration:none}a:hover{text-decoration:underline}header{position:sticky;top:0;z-index:5;padding:16px 22px;background:#071018f2;border-bottom:1px solid #213647;backdrop-filter:blur(12px)}h1{margin:0;font-size:22px}.sub,.muted,.tiny{color:#8da6b8}.tiny{font-size:12px}.clock{font-variant-numeric:tabular-nums;color:#d8e7f1;margin-top:5px}.wrap{max-width:2100px;margin:auto;padding:18px}.grid{display:grid;gap:12px}.kpis{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}.qa{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.ops{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.card{background:#0e1b26;border:1px solid #213647;border-radius:12px;padding:14px}.kpi b{font-size:26px;display:block}.green{color:#42d392}.yellow{color:#f6c95f}.orange{color:#f59e5f}.red{color:#ff6b6b}.blue{color:#6aaeff}.gray{color:#8da6b8}.section{margin-top:18px}.answers b{display:block;margin-bottom:4px}.alerts,.toolbar{display:flex;gap:8px;flex-wrap:wrap}.pill,.badge{border:1px solid #213647;border-radius:999px;padding:5px 8px;display:inline-block}.pill.critical,.badge.red{color:#ff9d9d;border-color:#6d2c2c}.pill.warning,.badge.yellow,.badge.orange{color:#f6d57b;border-color:#66552a}.badge.green{color:#66e6ad;border-color:#2f6d56}.badge.gray{color:#9fb0bd}.toolbar{margin:10px 0}input,select{background:#0a1721;border:1px solid #213647;color:#e9f2f8;padding:9px;border-radius:8px}input{min-width:280px}.tablewrap{overflow:auto;border:1px solid #213647;border-radius:12px;margin-top:10px}table{border-collapse:collapse;width:100%;min-width:2200px}th,td{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #172a38}th{position:sticky;top:92px;background:#0b1822;color:#a8bdcb;font-size:12px}.repo{font-weight:700}.blocked{color:#ff6b6b;font-weight:700}tr:hover{background:#102331}footer{text-align:center;color:#8da6b8;padding:24px}"""

pending_commit=summ.get("localPendingCommit",0);pending_push=summ.get("localPendingPush",0);behind=summ.get("localBehind",0);synced=summ.get("localSynced",0)
cards=[
("Repositories",summ.get("repositories",len(repos)),"blue"),("Open PRs",summ.get("openPrsIndexed",0),"blue"),("In progress",summ.get("inProgress",0),"yellow"),
("Review/defined ≠ implemented",review_only,"red" if review_only else "green"),("Blocked/conflict",summ.get("blockedIssues",0),"red" if summ.get("blockedIssues",0) else "green"),
("Pending commit",pending_commit,"orange" if pending_commit else "green"),("Pending push",pending_push,"red" if pending_push else "green"),
("Local behind",behind,"orange" if behind else "green"),("Pushed/synced",synced,"green"),("Critical alerts",summ.get("criticalAlerts",0),"red" if summ.get("criticalAlerts",0) else "green"),
("Prometheus",f'{prom.get("targets_up",0)}/{prom.get("targets_total",0)}',"green")
]

parts=['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codestra Mission Control</title><style>',css,'</style></head><body>']
parts.append('<header><h1>Codestra Mission Control</h1><div class="sub">GitHub · Linear · Notion · Local Git · Prometheus · Alertmanager · Grafana · SentinelX</div><div class="clock">Live local time: <b id="clock"></b> · Snapshot: '+e(s.get("generatedAt",""))+' · Local scan: '+e(s.get("localWorkCheckAt","not yet scanned"))+'</div></header><div class="wrap">')
parts.append('<div class="grid kpis">'+''.join(f'<div class="card kpi"><b class="{col}">{e(val)}</b><span class="muted">{e(label)}</span></div>' for label,val,col in cards)+'</div>')
parts.append('<div class="section"><h2>Completion truth</h2><div class="grid qa answers">')
parts.append('<div class="card"><b>Reviewed / Defined</b><span class="blue">Understanding, complaint analysis, audit, plan, specification or review.</span><div class="tiny">This is evidence that the problem was understood. It is NOT implementation.</div></div>')
parts.append('<div class="card"><b>Implemented</b><span class="orange">A code/config/data change must exist.</span><div class="tiny">Evidence can include local changes, local commits, a PR or merged code. A review document alone cannot satisfy this gate.</div></div>')
parts.append('<div class="card"><b>Verified / Complete</b><span class="green">Implementation plus verification evidence.</span><div class="tiny">Tests/CI and, where applicable, deployment/readback/runtime evidence must prove the requested outcome. Linear Done alone is not sufficient.</div></div>')
parts.append('</div></div>')
parts.append('<div class="section"><h2>Questions answered now</h2><div class="grid qa answers">')
qas=s.get("questionAnswers") or []
if qas:
    for q in qas:
        parts.append('<div class="card"><b>'+e(q.get("question",""))+'</b><span class="'+e(q.get("status","gray"))+'">'+e(q.get("answer","Unknown / Not Proven"))+'</span></div>')
else:
    parts.append('<div class="card"><b>Question coverage</b><span class="gray">Unknown / Not Proven — question-answer refresh has not run yet.</span></div>')
parts.append('</div></div>')
parts.append('<div class="section"><h2>Live operations</h2><div class="grid ops"><div class="card"><b>Codestra Prometheus</b><div class="green">'+e(prom.get("targets_up",0))+'/'+e(prom.get("targets_total",0))+' targets up</div></div><div class="card"><b>Alertmanager</b><div class="'+("red" if summ.get("criticalAlerts",0) else "green")+'">'+e(summ.get("activeAlerts",len(alerts)))+' active · '+e(summ.get("criticalAlerts",0))+' critical</div></div><div class="card"><b>Klyrow Prometheus</b><div class="green">'+e(kp.get("targets_up",0))+'/'+e(kp.get("targets_total",0))+' targets up</div></div><div class="card"><b>Telnexa Prometheus</b><div class="green">'+e(tp.get("targets_up",0))+'/'+e(tp.get("targets_total",0))+' targets up</div></div></div><div class="alerts">'+(''.join('<span class="pill '+e(a.get("severity",""))+'">'+e(a.get("severity",""))+' · '+e(a.get("name",""))+'</span>' for a in alerts) or '<span class="pill">No active alerts</span>')+'</div></div>')
parts.append('<div class="section"><h2>Repository mission queue</h2><div class="toolbar"><input id="search" placeholder="Search repo, mission, local status, completion truth…"><select id="filter"><option value="">All states</option><option value="notImplemented">Review/defined, implementation not proven</option><option value="doneUnproven">Done but completion not proven</option><option value="blocked">Blocked/conflict</option><option value="pendingPush">Pending push</option><option value="pendingCommit">Pending commit</option><option value="behind">Local behind</option><option value="synced">Pushed/synced</option><option value="In Progress">In Progress</option><option value="In Review">In Review</option><option value="Unlinked">Unlinked</option></select><select id="group"><option value="">All groups</option><option value="core">Core</option><option value="monitoring">Monitoring</option><option value="saas">Apps/SaaS</option></select></div><div class="tablewrap"><table><thead><tr><th>Repository</th><th>Goal / mission</th><th>Assignee / Linear status</th><th>Completion truth</th><th>PRs</th><th>Blocker</th><th>Local work lifecycle</th><th>Started / pending since</th><th>Git / push evidence</th><th>Latest commit / daily work</th><th>Actions</th></tr></thead><tbody id="repoRows"></tbody></table></div></div></div>')
repo_json=json.dumps(repos,separators=(",",":")).replace("</","<\\/")
parts.append('<script id="repo-data" type="application/json">'+repo_json+'</script>')
truth_json=json.dumps({k:{"label":v[0],"color":v[1],"note":v[2]} for k,v in truths.items()},separators=(",",":")).replace("</","<\\/")
parts.append('<script id="truth-data" type="application/json">'+truth_json+'</script>')
js=r"""<script>
const DATA=JSON.parse(document.getElementById('repo-data').textContent);
const TRUTH=JSON.parse(document.getElementById('truth-data').textContent);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tick(){document.getElementById('clock').textContent=new Date().toLocaleString(undefined,{dateStyle:'full',timeStyle:'medium'});}tick();setInterval(tick,1000);
function fmt(v){if(!v)return '<span class="muted">—</span>';const d=new Date(v);return isNaN(d)?esc(v):esc(d.toLocaleString());}
function row(r){
 const w=r.localWork||{state:r.local?'Local state pending scan':'Remote only',color:'gray',pending:false};
 const life='<span class="badge '+esc(w.color||'gray')+'">'+esc(w.state||'Unknown')+'</span>';
 const t=TRUTH[r.name]||{label:'Unknown',color:'gray',note:'No completion truth available.'};
 const truth='<span class="badge '+esc(t.color)+'">'+esc(t.label)+'</span><div class="tiny">'+esc(t.note)+'</div>';
 const prs=(r.prs||[]).length?r.prs.map(p=>'<div><a href="'+esc(p.url)+'">#'+p.number+' '+esc(p.title)+'</a></div>').join(''):'<span class="muted">0 indexed</span>';
 const blocker=r.blocked?'<a class="blocked" href="'+esc(r.blockerUrl)+'">'+esc(r.blocker)+'</a>':'<span class="green">No linked conflict</span>';
 const assignee=esc(r.assignee||'Unassigned');
 let git='<span class="muted">No local clone/state</span>';
 if(r.local){git='<b>'+esc(r.local.branch||'HEAD')+'</b> @ '+esc(r.local.head||'—')+'<div class="tiny">'+esc(r.local.path||'')+'</div><div>dirty '+Number(r.dirtyFiles||0)+' · ahead '+Number(r.maxAhead||0)+' · behind '+Number(r.maxBehind||0)+' · '+Number(r.worktreeCount||0)+' worktree(s)</div>';}
 const last=r.local?.last_commit?String(r.local.last_commit).split('|').map(esc).join('<br>'):'<span class="muted">Unavailable</span>';
 const since=w.dirtySince||w.unpushedSince||w.startedAt||'';
 return '<tr><td><div class="repo"><a href="'+esc(r.github)+'">'+esc(r.name)+'</a></div><div class="tiny">'+esc(r.visibility)+' · '+esc(r.group||'')+'</div></td>'+
 '<td><a href="'+esc(r.linearUrl)+'">'+esc(r.linearIssue)+' '+esc(r.goal)+'</a></td>'+
 '<td><b>'+assignee+'</b><div>'+esc(r.linearStatus)+'</div></td><td>'+truth+'</td><td>'+prs+'</td><td>'+blocker+'</td><td>'+life+'<div class="tiny">checked '+fmt(w.checkedAt)+'</div></td>'+
 '<td>'+fmt(since)+'<div class="tiny">'+(w.unpushedSince?'Unpushed since '+fmt(w.unpushedSince):'')+'</div></td><td>'+git+'</td><td class="tiny">'+last+'</td>'+
 '<td><a href="'+esc(r.notionUrl)+'">Notion</a> · <a href="'+esc(r.github)+'/pulls">PRs</a> · <a href="'+esc(r.github)+'/actions">CI</a></td></tr>';
}
function render(){const q=document.getElementById('search').value.toLowerCase(),f=document.getElementById('filter').value,g=document.getElementById('group').value;const list=DATA.filter(r=>{const w=r.localWork||{},t=TRUTH[r.name]||{};const hay=[r.name,r.goal,r.linearStatus,r.blocker,r.assignee,r.local?.branch,r.local?.head,w.state,t.label,t.note].join(' ').toLowerCase();if(q&&!hay.includes(q))return false;if(g&&r.group!==g)return false;if(f==='notImplemented'&&!['Review only / implementation not proven','Defined / implementation not proven'].includes(t.label))return false;if(f==='doneUnproven'&&!String(t.label).startsWith('Done status /'))return false;if(f==='blocked'&&!r.blocked)return false;if(f==='pendingPush'&&!(w.pendingPush>0||r.maxAhead>0))return false;if(f==='pendingCommit'&&!(w.pendingCommit>0||r.dirtyFiles>0))return false;if(f==='behind'&&!(w.behind>0||r.maxBehind>0))return false;if(f==='synced'&&w.state!=='Pushed / synced')return false;if(f&&!['notImplemented','doneUnproven','blocked','pendingPush','pendingCommit','behind','synced'].includes(f)&&r.linearStatus!==f)return false;return true});document.getElementById('repoRows').innerHTML=list.map(row).join('');}
document.querySelectorAll('input,select').forEach(x=>x.addEventListener('input',render));render();
</script>"""
parts.append(js);parts.append('<footer><b>Completion rule:</b> Review/analysis/definition does not equal implementation. Implementation does not equal verified completion. Local push state uses the last-known upstream tracking ref; the hourly cloud watch refreshes remote truth.</footer></body></html>')
with open(OUT,"w",encoding="utf-8") as f:f.write(''.join(parts))
print(json.dumps({"dashboard":OUT,"repos":len(repos),"reviewOnlyOrUnproven":review_only,"localCheckAt":s.get("localWorkCheckAt"),"pendingCommit":pending_commit,"pendingPush":pending_push,"behind":behind,"synced":synced}))
