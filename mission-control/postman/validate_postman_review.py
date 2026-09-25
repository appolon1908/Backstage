#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
COLLECTION=ROOT/"Codestra-API-Review.postman_collection.json"
ENV=ROOT/"Codestra-API-Review.postman_environment.json"

SAFE_METHODS={"GET","HEAD","OPTIONS"}

collection=json.loads(COLLECTION.read_text(encoding="utf-8"))
environment=json.loads(ENV.read_text(encoding="utf-8"))

errors=[]
summary={"requests":0,"tested_requests":0,"safe_requests":0,"effectful_requests":0,"folders":[]}

def walk(items,parents=()):
    for item in items or []:
        name=item.get("name","")
        if item.get("item") is not None:
            folder=parents+(name,)
            if len(folder)==1:
                summary["folders"].append(name)
            walk(item.get("item"),folder)
        req=item.get("request")
        if not req:
            continue
        summary["requests"]+=1
        method=str(req.get("method","")).upper()
        top=parents[0] if parents else ""
        events=item.get("event") or []
        tests=[e for e in events if e.get("listen")=="test"]
        prereq=[e for e in events if e.get("listen")=="prerequest"]
        if tests:
            summary["tested_requests"]+=1
        else:
            errors.append(f"request_without_test:{'/'.join(parents+(name,))}")
        if top.startswith("90 "):
            summary["effectful_requests"]+=1
            scripts="\n".join(
                line
                for e in prereq
                for line in ((e.get("script") or {}).get("exec") or [])
            )
            if "pm.execution.skipRequest()" not in scripts or "RUN_EFFECTFUL" not in scripts:
                errors.append(f"effectful_request_missing_fail_closed_skip:{name}")
        else:
            summary["safe_requests"]+=1
            if method not in SAFE_METHODS:
                errors.append(f"unsafe_method_outside_effectful_folder:{method}:{name}")

values={v.get("key"):v.get("value") for v in environment.get("values",[])}
if values.get("RUN_EFFECTFUL")!="false":
    errors.append("RUN_EFFECTFUL_must_default_false")
for key in ("bearer_token","wrong_audience_token"):
    if values.get(key):
        errors.append(f"secret_value_must_be_empty:{key}")
for key in ("mission_control_url","middleware_url","kong_url","caddy_url"):
    value=str(values.get(key,""))
    if "api.codestra.co" in value:
        errors.append(f"production_url_forbidden_in_safe_environment:{key}")

expected_folders=[
    "00 Preflight",
    "01 Security Denials",
    "02 Read-only Middleware Contracts",
    "03 Edge Parity",
    "04 Runtime Readback",
    "90 Effectful Negative Tests - Disabled by Default",
]
if summary["folders"]!=expected_folders:
    errors.append("folder_order_or_names_drift")

walk(collection.get("item"))
summary["errors"]=errors
print(json.dumps(summary,sort_keys=True))
if errors:
    raise SystemExit(1)
