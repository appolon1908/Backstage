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
def c(v):return {"green":"green","red":"red","orange":"orange","gray":"gray","yellow":"yellow","blue":"blue"}.get(v,"gray")
css="""*{box-sizing:border-box}body{margin:0;font:14px/1.45 Inter,system-ui;background:#071018;color:#e9f2f8}a{color:#8fc6ff;text-decoration:none}a:hover{text-decoration:underline}header{position:sticky;top:0;z-index:5;padding:16px 22px;background:#071018f2;border-bottom:1px solid #213647;backdrop-filter:blur(12px)}h1{margin:0;font-size:22px}.sub,.muted,.tiny{color:#8da6b8}.tiny{font-size:12px}.clock{font-variant-numeric:tabular-nums;color:#d8e7f1;margin-top:5px}.wrap{max-width:2000px;margin:auto;padding:18px}.grid{display:grid;gap:12px}.kpis{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}.qa{grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}.ops{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.card{background:#0e1b26;border:1px solid #213647;border-radius:12px;padding:14px}.kpi b{font-size:26px;display:block}.green{color:#42d392}.yellow{color:#f6c95f}.orange{color:#f59e5f}.red{color:#ff6b6b}.blue{color:#6aaeff}.gray{color:#8da6b8}.section{margin-top:18px}.answers b{display:block;margin-bottom:4px}.alerts,.toolbar{display:flex;gap:8px;flex-wrap:wrap}.pill,.badge{border:1px solid #213647;border-radius:999px;padding:5px 8px;display:inline-block}.pill.critical,.badge.red{color:#ff9d9d;border-color:#6d2c2c}.pill.warning,.badge.yellow,.badge.orange{color:#f6d57b;border-color:#66552a}.badge.green{color:#66e6ad;border-color:#2f6d56}.badge.gray{color:#9fb0bd}.toolbar{margin:10px 0}input,select{background:#0a1721;border:1px solid #213647;color:#e9f2f8;padding:9px;border-radius:8px}input{min-width:280px}.tablewrap{overflow:auto;border:1px solid #213647;border-radius:12px;margin-top:10px}table{border-collapse:collapse;width:100%;min-width:1900px}th,td{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #172a38}th{position:sticky;top:92px;background:#0b1822;color:#a8bdcb;font-size:12px}.repo{font-weight:700}.blocked{color:#ff6b6b;font-weight:700}tr:hover{background:#102331}footer{text-align:center;color:#8da6b8;padding:24px}"""
pending_commit=summ.get("localPendingCommit",0);pending_push=summ.get("localPendingPush",0);behind=summ.get("localBehind",0);synced=summ.get("localSynced",0)
cards=[
("Repositories",summ.get("repositories",len(repos)),"blue"),("Open PRs",summ.get("openPrsIndexed",0),"blue"),("In progress",summ.get("inProgress",0),"yellow"),
("Blocked/conflict",summ.get("blockedIssues",0),"red" if summ.get("blockedIssues",0) else "green"),("Pending commit",pending_commit,"orange" if pending_commit else "green"),
("Pending push",pending_push,"red" if pending_push else "green"),("Local behind",behind,"orange" if behind else "green"),("Pushed/synced",synced,"green"),
("Critical alerts",summ.get("criticalAlerts",0),"red" if summ.get("criticalAlerts",0) else "green"),("Prometheus",f'{prom.get("targets_up",0)}/{prom.get("targets_total",0)}',"green")
]
parts=['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codestra Mission Control</title><style>',css,'</style></head><body>']
parts.append('<header><h1>Codestra Mission Control</h1><div class="sub">GitHub · Linear · Notion · Local Git · Prometheus · Alertmanager · Grafana · SentinelX</div><div class="clock">Live local time: <b id="clock"></b> · Snapshot: '+e(s.get("generatedAt",""))+' · Local scan: '+e(s.get("localWorkCheckAt","not yet scanned"))+'</div></header><div class="wrap">')
parts.append('<div class="grid kpis">'+''.join(f'<div class="card kpi"><b class="{col}">{e(val)}</b><span class="muted">{e(label)}</span></div>' for label,val,col in cards)+'</div>')
parts.append('<div class="section"><h2>Questions answered now</h2><div class="grid qa answers">')
attention=summ.get("criticalAlerts",0)+summ.get("blockedIssues",0)+pending_commit+pending_push
parts.append(f'<div class="card"><b>What needs attention?</b><span class="{"red" if attention else "green"}">{attention} actionable signals</span><div class="tiny">Critical alerts, blocked/conflict missions, pending commits and unpushed commits.</div></div>')
parts.append(f'<div class="card"><b>What is still only local?</b><span class="{"red" if pending_push else "green"}">{pending_push} worktree(s) committed but not pushed</span><div class="tiny">{pending_commit} worktree(s) also have uncommitted changes.</div></div>')
parts.append(f'<div class="card"><b>What is pushed?</b><span class="green">{synced} worktree(s) synced</span><div class="tiny">{behind} pushed worktree(s) are now behind their last-known upstream ref.</div></div>')
parts.append(f'<div class="card"><b>Is runtime healthy?</b><span class="{"red" if summ.get("criticalAlerts",0) else "green"}">{prom.get("targets_up",0)}/{prom.get("targets_total",0)} Prometheus targets up · {summ.get("criticalAlerts",0)} critical alerts</span></div>')
parts.append('</div></div>')
parts.append('<div class="section"><h2>Live operations</h2><div class="grid ops"><div class="card"><b>Codestra Prometheus</b><div class="green">'+e(prom.get("targets_up",0))+'/'+e(prom.get("targets_total",0))+' targets up</div></div><div class="card"><b>Alertmanager</b><div class="'+("red" if summ.get("criticalAlerts",0) else "green")+'">'+e(summ.get("activeAlerts",len(alerts)))+' active · '+e(summ.get("criticalAlerts",0))+' critical</div></div><div class="card"><b>Klyrow Prometheus</b><div class="green">'+e(kp.get("targets_up",0))+'/'+e(kp.get("targets_total",0))+' targets up</div></div><div class="card"><b>Telnexa Prometheus</b><div class="green">'+e(tp.get("targets_up",0))+'/'+e(tp.get("targets_total",0))+' targets up</div></div></div><div class="alerts">'+(''.join('<span class="pill '+e(a.get("severity",""))+'">'+e(a.get("severity",""))+' · '+e(a.get("name",""))+'</span>' for a in alerts) or '<span class="pill">No active alerts</span>')+'</div></div>')
parts.append('<div class="section"><h2>Repository mission queue</h2><div class="toolbar"><input id="search" placeholder="Search repo, mission, local status, branch…"><select id="filter"><option value="">All states</option><option value="blocked">Blocked/conflict</option><option value="pendingPush">Pending push</option><option value="pendingCommit">Pending commit</option><option value="behind">Local behind</option><option value="synced">Pushed/synced</option><option value="In Progress">In Progress</option><option value="In Review">In Review</option><option value="Unlinked">Unlinked</option></select><select id="group"><option value="">All groups</option><option value="core">Core</option><option value="monitoring">Monitoring</option><option value="saas">Apps/SaaS</option></select></div><div class="tablewrap"><table><thead><tr><th>Repository</th><th>Goal / mission</th><th>Assignee / status</th><th>PRs</th><th>Blocker</th><th>Local work lifecycle</th><th>Started / pending since</th><th>Git / push evidence</th><th>Latest commit / daily work</th><th>Actions</th></tr></thead><tbody id="repoRows"></tbody></table></div></div></div>')
repo_json=json.dumps(repos,separators=(",",":")).replace("</","<\\/")
parts.append('<script id="repo-data" type="application/json">'+repo_json+'</script>')
js=r"""<script>
const DATA=JSON.parse(document.getElementById('repo-data').textContent);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tick(){document.getElementById('clock').textContent=new Date().toLocaleString(undefined,{dateStyle:'full',timeStyle:'medium'});}tick();setInterval(tick,1000);
function fmt(v){if(!v)return '<span class="muted">—</span>';const d=new Date(v);return isNaN(d)?esc(v):esc(d.toLocaleString());}
function row(r){
 const w=r.localWork||{state:r.local?'Local state pending scan':'Remote only',color:'gray',pending:false};
 const badge='<span class="badge '+esc(w.color||'gray')+'">'+esc(w.state||'Unknown')+'</span>';
 const prs=(r.prs||[]).length?r.prs.map(p=>'<div><a href="'+esc(p.url)+'">#'+p.number+' '+esc(p.title)+'</a></div>').join(''):'<span class="muted">0 indexed</span>';
 const blocker=r.blocked?'<a class="blocked" href="'+esc(r.blockerUrl)+'">'+esc(r.blocker)+'</a>':'<span class="green">No linked conflict</span>';
 const assignee=esc(r.assignee||'Unassigned');
 let git='<span class="muted">No local clone/state</span>';
 if(r.local){git='<b>'+esc(r.local.branch||'HEAD')+'</b> @ '+esc(r.local.head||'—')+'<div class="tiny">'+esc(r.local.path||'')+'</div><div>dirty '+Number(r.dirtyFiles||0)+' · ahead '+Number(r.maxAhead||0)+' · behind '+Number(r.maxBehind||0)+' · '+Number(r.worktreeCount||0)+' worktree(s)</div>';}
 const last=r.local?.last_commit?String(r.local.last_commit).split('|').map(esc).join('<br>'):'<span class="muted">Unavailable</span>';
 const since=w.dirtySince||w.unpushedSince||w.startedAt||'';
 return '<tr><td><div class="repo"><a href="'+esc(r.github)+'">'+esc(r.name)+'</a></div><div class="tiny">'+esc(r.visibility)+' · '+esc(r.group||'')+'</div></td>'+
 '<td><a href="'+esc(r.linearUrl)+'">'+esc(r.linearIssue)+' '+esc(r.goal)+'</a></td>'+
 '<td><b>'+assignee+'</b><div>'+esc(r.linearStatus)+'</div></td><td>'+prs+'</td><td>'+blocker+'</td><td>'+badge+'<div class="tiny">checked '+fmt(w.checkedAt)+'</div></td>'+
 '<td>'+fmt(since)+'<div class="tiny">'+(w.unpushedSince?'Unpushed since '+fmt(w.unpushedSince):'')+'</div></td><td>'+git+'</td><td class="tiny">'+last+'</td>'+
 '<td><a href="'+esc(r.notionUrl)+'">Notion</a> · <a href="'+esc(r.github)+'/pulls">PRs</a> · <a href="'+esc(r.github)+'/actions">CI</a></td></tr>';
}
function render(){const q=document.getElementById('search').value.toLowerCase(),f=document.getElementById('filter').value,g=document.getElementById('group').value;const list=DATA.filter(r=>{const w=r.localWork||{};const hay=[r.name,r.goal,r.linearStatus,r.blocker,r.assignee,r.local?.branch,r.local?.head,w.state].join(' ').toLowerCase();if(q&&!hay.includes(q))return false;if(g&&r.group!==g)return false;if(f==='blocked'&&!r.blocked)return false;if(f==='pendingPush'&&!(w.pendingPush>0||r.maxAhead>0))return false;if(f==='pendingCommit'&&!(w.pendingCommit>0||r.dirtyFiles>0))return false;if(f==='behind'&&!(w.behind>0||r.maxBehind>0))return false;if(f==='synced'&&w.state!=='Pushed / synced')return false;if(f&&!['blocked','pendingPush','pendingCommit','behind','synced'].includes(f)&&r.linearStatus!==f)return false;return true});document.getElementById('repoRows').innerHTML=list.map(row).join('');}
document.querySelectorAll('input,select').forEach(x=>x.addEventListener('input',render));render();
</script>"""
parts.append(js);parts.append('<footer>Local push state is evaluated against the last-known upstream tracking ref. The hourly cloud Mission Control Watch refreshes remote GitHub truth.</footer></body></html>')
with open(OUT,"w",encoding="utf-8") as f:f.write(''.join(parts))
print(json.dumps({"dashboard":OUT,"repos":len(repos),"localCheckAt":s.get("localWorkCheckAt"),"pendingCommit":pending_commit,"pendingPush":pending_push,"behind":behind,"synced":synced}))
