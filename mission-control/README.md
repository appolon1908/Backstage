# Codestra Mission Control Dashboard

Source of truth: GitHub + Linear + Notion + local Git + Prometheus/Alertmanager/Grafana + SentinelX.

Current snapshot: 59 repos; 100 open PRs indexed; 137 Linear issues; 33 in progress; 3 blocked/conflict issues; Codestra Prometheus 38/38 up; 15 active alerts (11 critical).

Staging action: PAS-151 remains NOT READY. The previously missing JWT/JWKS fallback now exists as draft, mergeable Kong PR #116 (local JWKS render, DB-less parse, and 3/3 regression tests pass), but runtime apply is NO, no hosted workflow run exists for its head, and PAS-190 remains in force. The canonical Middleware staging application plane is still intentionally stopped pending a current immutable candidate. Do not restart the stale stack as a shortcut.

Local sync action: clean Appolon canonical main branches are behind upstream — Breero.com 1, klyrow.com 2, Middleware- 1, Odoo 1 commit(s). No Prometheus target is down and the alert set is unchanged.
