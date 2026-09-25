import os, json, datetime, threading, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE=r"C:\Users\Usuario\01_DEVELOPMENT\Mission-Control"
QUEUE=os.path.join(BASE,"actions_queue.json")
LOCK=threading.Lock()
HOST="127.0.0.1"
PORT=8765

os.makedirs(BASE,exist_ok=True)
if not os.path.exists(QUEUE):
    with open(QUEUE,"w",encoding="utf-8") as f:json.dump({"items":[]},f,indent=2)

def now():
    return datetime.datetime.now().astimezone().isoformat()

def read_json(path,default):
    try:
        with open(path,encoding="utf-8-sig") as f:return json.load(f)
    except:return default

def write_queue(doc):
    tmp=QUEUE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:json.dump(doc,f,indent=2,ensure_ascii=False)
    os.replace(tmp,QUEUE)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=BASE,**kwargs)

    def log_message(self,fmt,*args):
        return

    def guess_type(self,path):
        ctype=super().guess_type(path)
        if ctype.startswith("text/") and "charset=" not in ctype:
            return ctype+"; charset=utf-8"
        if ctype=="application/json":
            return "application/json; charset=utf-8"
        return ctype

    def end_headers(self):
        self.send_header("Cache-Control","no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma","no-cache")
        self.send_header("Expires","0")
        self.send_header("X-Content-Type-Options","nosniff")
        super().end_headers()

    def send_json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path)
        if parsed.path=="/":
            self.path="/dashboard.html"
            return super().do_GET()
        if parsed.path=="/api/health":
            return self.send_json({"ok":True,"service":"Codestra Mission Control Local Server","time":now(),"port":PORT})
        if parsed.path=="/api/snapshot":
            return self.send_json(read_json(os.path.join(BASE,"snapshot.json"),{}))
        if parsed.path=="/api/actions":
            return self.send_json(read_json(QUEUE,{"items":[]}))
        return super().do_GET()

    def do_POST(self):
        parsed=urllib.parse.urlparse(self.path)
        length=int(self.headers.get("Content-Length","0") or 0)
        if length<=0 or length>100000:
            return self.send_json({"ok":False,"error":"invalid request size"},400)
        try:
            body=json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.send_json({"ok":False,"error":"invalid JSON"},400)

        if parsed.path=="/api/action":
            kind=str(body.get("kind","")).strip().lower()
            repo=str(body.get("repo","")).strip()
            issue=str(body.get("issueId","")).strip()
            title=str(body.get("title","")).strip()
            text=str(body.get("body","")).strip()
            priority=str(body.get("priority","Medium")).strip()
            stage=str(body.get("stage","")).strip().lower()
            if kind not in {"task","comment","stage"}:
                return self.send_json({"ok":False,"error":"kind must be task, comment, or stage"},400)
            if not repo:
                return self.send_json({"ok":False,"error":"repo is required"},400)
            snap=read_json(os.path.join(BASE,"snapshot.json"),{})
            known={str(x.get("name")) for x in snap.get("repositories",[])}
            if known and repo not in known:
                return self.send_json({"ok":False,"error":"unknown repository"},400)
            if kind=="comment" and (not issue or not text):
                return self.send_json({"ok":False,"error":"comment requires a linked Linear issue and body"},400)
            if kind=="task" and not title:
                return self.send_json({"ok":False,"error":"task title is required"},400)
            if kind=="stage":
                if not issue:
                    return self.send_json({"ok":False,"error":"stage change requires a linked Linear issue"},400)
                if stage not in {"defined","implement","verify","done"}:
                    return self.send_json({"ok":False,"error":"invalid stage"},400)
                if stage=="done":
                    mission=((snap.get("remoteRefresh") or {}).get("missions") or {}).get(issue) or {}
                    if mission.get("complete") is not True:
                        return self.send_json({"ok":False,"error":"Done is evidence-locked: verification/completion is not proven for this mission"},409)
            if len(title)>300 or len(text)>12000:
                return self.send_json({"ok":False,"error":"action content too long"},400)
            aid="MCA-"+datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
            item={
                "id":aid,"createdAt":now(),"updatedAt":now(),"status":"pending",
                "kind":kind,"repo":repo,"issueId":issue,"title":title,"body":text,
                "priority":priority,"stage":stage,"requestedBy":"Mission Control Dashboard",
                "delivery":{"target":"Linear","attempts":0,"externalId":"","url":"","error":""}
            }
            with LOCK:
                q=read_json(QUEUE,{"items":[]})
                q.setdefault("items",[]).append(item)
                write_queue(q)
            return self.send_json({"ok":True,"action":item},201)

        if parsed.path.startswith("/api/action/") and parsed.path.endswith("/cancel"):
            aid=parsed.path.split("/")[3]
            with LOCK:
                q=read_json(QUEUE,{"items":[]})
                hit=None
                for item in q.get("items",[]):
                    if item.get("id")==aid:
                        hit=item
                        if item.get("status")=="pending":
                            item["status"]="cancelled";item["updatedAt"]=now()
                        break
                if not hit:return self.send_json({"ok":False,"error":"action not found"},404)
                write_queue(q)
            return self.send_json({"ok":True,"action":hit})
        return self.send_json({"ok":False,"error":"not found"},404)

if __name__=="__main__":
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    server.serve_forever()
