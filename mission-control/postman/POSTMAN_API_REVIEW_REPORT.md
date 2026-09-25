# Codestra Postman API Review — Clean Report

Generated: 2026-09-25  
Scope: Middleware V3, Kong V3 parity, Caddy edge certification, Mission Control readback  
Mode: **safe by default / no production effects**

## Executive result

The current Postman estate has good source ownership and deterministic generation, but the collections have mixed purposes.

- **Middleware OpenAPI collection** is a broad generated API inventory, not a certification suite.
- **Kong parity collection** is a route-parity inventory, not a response-assertion suite.
- **Caddy edge collection** is the strongest certification artifact because it already contains explicit denial assertions.
- Keycloak and Odoo do not currently expose repository-owned Postman collections in the reviewed default-branch search.
- Klyrow documents Postman regeneration/certification as a required gate, but no repository-owned collection surfaced in the reviewed search.

The new Mission Control Postman workflow separates read-only certification from effectful probes and keeps effectful execution disabled by default.

## Source evidence reviewed

| Surface | Source artifact | Evidence |
|---|---|---|
| Middleware | `postman/generated/Middleware-OpenAPI.postman_collection.json` | blob `4ebe53722637e1f6c653835372466048cbed3fe3` |
| Middleware DB gate | `postman/certification-manifest.json` | blob `10f3873304bd225170c987244706a6e34a1317b6`; production effects default to 0 / GO=NO |
| Kong | `postman/Kong-V3-Integration-Parity.postman_collection.json` | blob `61b42ce3958751014f64d90f0fca78bbeb4bfce5` |
| Kong environment | `postman/Kong-V3-Integration-Parity.postman_environment.json` | safe local, `RUN_KONG_V3_PARITY=false` |
| Caddy | `postman/Caddy-V3-Edge-Certification.postman_collection.json` | blob `0b502785a0e93719bbcc40bae3a366bfc37bf8f1` |
| Caddy environment | `postman/Caddy-V3-Edge-Certification.postman_environment.json` | safe local, `RUN_CADDY_EDGE_CERTIFICATION=false` |

## Quantitative review

### Middleware

- Requests: **331**
- GET: **189**
- POST: **136**
- PATCH: **6**
- Requests with Postman response tests: **0**
- Requests carrying Authorization: **326**
- Requests carrying Idempotency-Key: **100**
- Requests carrying X-Correlation-ID: **98**
- Mutating/effectful-shape requests: **142**
- Mutating requests without response tests: **142**

Interpretation: the generated collection accurately mirrors the OpenAPI, but it must not be treated as runtime certification by itself. It needs a separate safe certification layer with explicit status/schema/denial/readback assertions.

### Kong

- Requests: **50**
- GET: **19**
- POST: **25**
- PATCH: **5**
- PUT: **1**
- Requests with Postman response tests: **0**
- Requests carrying Authorization: **42**
- Requests carrying X-Correlation-ID: **50**
- Requests carrying Idempotency-Key: **19**
- Mutating/effectful-shape requests: **31**
- Mutating requests without response tests: **31**

Interpretation: strong correlation/header discipline, but parity data alone does not certify behavior. A distinct response-assertion workflow is required.

### Caddy

- Requests: **14**
- GET: **10**
- POST: **4**
- Requests with Postman tests: **9**
- Private-boundary probes: **6**
- Private-boundary probes with explicit 404 assertions: present
- One effectful-shaped auth-negative POST has no assertion in the original collection.

Interpretation: Caddy is closest to a true certification collection. Its denial tests should be the model for the other surfaces.

## Important gaps

1. **Inventory vs certification is mixed**
   - Generated OpenAPI/route inventories should remain generated and immutable.
   - Certification must live in a separate collection with explicit assertions.

2. **Mutation safety is not centralized**
   - Middleware/Kong contain many POST/PATCH/PUT routes.
   - A reviewer can accidentally run the full collection against a live environment.
   - The new review workflow places all effectful requests under a separately named folder and requires `RUN_EFFECTFUL=true`.

3. **Response assertions are missing**
   - Middleware and Kong currently have zero per-request response tests in the reviewed collections.
   - This prevents those collections from proving auth, denial, response shape, runtime continuity, or readback.

4. **Header policy is inconsistent**
   - Idempotency and correlation are present on many command routes but not universal across effectful-shaped routes.
   - Each mutating contract should explicitly declare whether Idempotency-Key and X-Correlation-ID are required, optional, or forbidden.

5. **Environment gates are fragmented**
   - Kong and Caddy already have safe-local switches.
   - Middleware DB certification also has production-safe defaults.
   - A common top-level safe-review environment was missing.

6. **Keycloak/Odoo/Klyrow coverage is incomplete**
   - No repository-owned Keycloak or Odoo Postman collection surfaced in the reviewed default-branch search.
   - Klyrow documentation requires Postman regeneration/certification, but no concrete collection surfaced in this review.
   - These should become separate provider/application collections, not be stuffed into Middleware.

## New separated workflow

Published under `mission-control/postman/`.

### 00 Preflight

Read-only:
- Mission Control health
- Middleware kernel describe
- Kong kernel describe
- Caddy kernel describe

Rules:
- no 5xx
- authenticated calls require 2xx when a bearer token is supplied

### 01 Security Denials

Read-only negative checks:
- Caddy `/internal/*` denied
- Caddy `/metrics` denied
- Caddy private DB health denied
- Kong `/internal/health` denied
- Kong `/metrics` denied

Expected result: **404** for public/private boundary probes.

### 02 Read-only Middleware Contracts

Read-only probes:
- services
- connectors
- activity
- email identities
- SMS identities
- telephony assignments

No business writes are performed.

### 03 Edge Parity

Read-only Kong/Caddy parity:
- services status parity
- connectors status parity

This verifies the public edge and Kong return equivalent status behavior for the same route family.

### 04 Runtime Readback

Read-only:
- Mission Control folder-sync state
- Mission Control action queue
- direct-private Middleware database health

This separates control-plane state from edge certification.

### 90 Effectful Negative Tests — Disabled by Default

Contains mutating-shaped auth-negative requests only.

Each request:
- checks `RUN_EFFECTFUL`
- invokes `pm.execution.skipRequest()` unless explicitly enabled
- expects only denial statuses `401/403/404`

Default environment:
- `RUN_EFFECTFUL=false`
- tokens empty
- loopback/private URLs only
- no production hostname

## Certification rules

A green Postman API review should mean all of the following:

- static guard passes
- every request has at least one assertion
- non-effectful folders contain only GET/HEAD/OPTIONS
- effectful folder is fail-closed unless `RUN_EFFECTFUL=true`
- safe environment contains no real token
- safe environment contains no production public hostname
- private routes are denied at Caddy/Kong public edges
- authenticated read-only requests are 2xx
- no reviewed endpoint returns 5xx
- runtime readback is current enough for the intended gate

A collection import, successful request transmission, or source-only generation is **not** sufficient to call the APIs certified.

## Files added

- `mission-control/postman/Codestra-API-Review.postman_collection.json`
- `mission-control/postman/Codestra-API-Review.postman_environment.json`
- `mission-control/postman/validate_postman_review.py`
- `.github/workflows/mission-control-postman-review.yml`

## Current gate

**STATIC WORKFLOW IMPLEMENTED. RUNTIME EXECUTION PENDING WORKSTATION RECONNECT.**

The desktop/Appolon Sentinel agents disconnected before Newman/Postman runtime execution could be performed. No runtime pass is claimed. When either workstation reconnects, run the safe folders first and keep folder 90 disabled until an explicit no-effect auth-negative certification window is approved.
