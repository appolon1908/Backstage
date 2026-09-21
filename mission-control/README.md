# Codestra Mission Control Dashboard

Source of truth: GitHub + Linear + Notion + local Git + Prometheus/Alertmanager/Grafana + SentinelX.

Current snapshot: 59 repos; 100 open PRs indexed; 137 Linear issues; 33 in progress; 3 blocked/conflict issues; Codestra Prometheus 38/38 up; 15 active alerts (11 critical).

Staging action: PAS-151 is NOT READY. No governed Kong Enterprise license artifact is present on the connected servers (or certified JWT/JWKS fallback), and the canonical Middleware staging application plane is intentionally stopped because its old compose references stale mixed images. Do not restart the old stack as a shortcut.

Local sync action: clean Appolon canonical main branches are behind upstream — Breero.com 1, klyrow.com 2, Middleware- 1, Odoo 1 commit(s). No Prometheus target is down and the alert set is unchanged.
