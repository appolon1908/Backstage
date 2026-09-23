# Codestra Mission Control Dashboard

Source of truth: GitHub + Linear + Notion + Appolon local Git + Prometheus/Alertmanager/Grafana + SentinelX. The dashboard is a derived read model and governed action surface; field authority remains with the owning system.

Current reconciliation: 61 repositories; 279 open PRs indexed by the last complete portfolio inventory; 150 Linear issues; 35 In Progress; 5 In Review; 3 blocked/conflict issue signals. Appolon local truth is 27 worktrees across 13 repositories with 6 pending-commit, 2 pending-push, 8 behind, 11 synced, and 0 scan errors.

Runtime: Prometheus is 43/43 targets up (Codestra 38/38, Klyrow 2/2, Telnexa 3/3). Six alerts remain active/firing, including three critical: MiddlewareDatabaseMigrationMismatch, KlyrowEventDeliveryStalled, and KlyrowUsageDeliveryStalled. Checked Grafana health is OK.

Completion truth is fail-closed. No mission in the refreshed evidence set is independently proven Verified/Complete today. Staging remains NOT READY and Production remains NO GO.

Release blockers: PAS-190 remains the hosted GitHub Actions execution-capacity blocker. DJONE PAS-252 remains Implemented / Verification Blocked at exact main HEAD 99234f8f762cff4b1bb2f927bfa100e13c61a795 because exact-head run 35820382136 failed with test and compose jobs reporting steps=[]. Middleware PAS-61 at PR #310 remains Implemented / In Review, Draft, and RED_ZERO_STEP. Do not treat review/specification or material implementation alone as completion.

Dashboard authority: Appolon Mission-Control application files are synchronized to the committed Backstage authority after recurring drift in Build-Question-Answers.py was repaired to blob 7f480bc88399dcf745077b2b80f5f5dac52d4b28. The local server was restarted only because application source changed; http://127.0.0.1:8765/api/health is healthy. Required V2 Executive, Repository Focus, Work Board, Runtime, Incomplete Work and Actions surfaces are present, including Table, Kanban, Timeline and My Work views.

The dashboard action queue currently has no pending items. No automatic push, merge, reset, clean, stash, discard, Done transition, or gate bypass was performed.
