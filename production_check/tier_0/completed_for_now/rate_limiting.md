# Production Concern: Rate Limiting (Tier 0)

Focus: abuse prevention and load control at API, queue, and expensive downstream boundaries.

## Release Blockers

1. **[FIXED] API request rate limiting now exists at IP/user levels** (`backend/router.py`, `backend/app.py`, `backend/services/rate_limit/*`)  
   Global IP limits and route-specific user/IP limits are now enforced for active API endpoints.

2. **[FIXED] Public endpoint abuse protection added** (`backend/router.py`, `backend/services/rate_limit/*`)  
   `/start-hunt` and `/health` are now covered by dedicated limits, reducing unbounded hit patterns.

3. **[OPEN] No downstream provider call-rate guards** (pipeline-wide)  
   OpenAI/AssemblyAI/Firecrawl/SearXNG/Firebase calls still do not have explicit token-bucket/leaky-bucket style controls.

## High Severity

4. **[PARTIALLY FIXED] `hunts_limit` remains quota-like, but request-rate controls now exist separately** (`backend/router.py`, `backend/db/database.py`, `backend/services/rate_limit/*`)  
   `hunts_limit` is still active-hunt quota logic, but short-window request frequency and burst behavior are now controlled by dedicated rate-limiter policies.

5. **[FIXED] Burst control added for expensive workflow trigger** (`backend/router.py`, `backend/services/rate_limit/*`)  
   `/start-hunt` now has per-user request limiting and duplicate-submit cooldown control.

6. **[OPEN] No queue ingress throttling or producer backpressure policy** (`backend/rmq/publisher.py`, `backend/orchestrator.py`)  
   Task/workflow publish paths still do not enforce explicit throughput caps when downstream workers are saturated.

7. **[FIXED] Route-level distinction between cheap and expensive limits implemented** (`backend/router.py`, `backend/services/rate_limit/policy.py`)  
   Health/read/write routes now use different policies rather than a single open behavior.

## Important Gaps

8. **[OPEN] No adaptive limiting based on dependency health** (pipeline-wide)  
   During upstream degradation, the system still does not tighten acceptance rate automatically to protect stability.

9. **[OPEN] No account-tier/role-aware rate-limit policies** (`backend/db/models/user_hunt_limit.py`, `backend/db/database.py`)  
   Current limits are static by route and do not vary by plan/tier/role.

10. **[PARTIALLY FIXED] Dedupe cooldown exists, but no idempotency-key contract** (`backend/router.py`, `backend/db/database.py`, `backend/services/rate_limit/*`)  
   Same-user same-video cooldown now exists, but there is still no explicit idempotency key protocol across API/queue workflow boundaries.

11. **[PARTIALLY FIXED] Rate-limit rejection observability added, but metrics/near-limit signals are missing** (`backend/services/rate_limit/dependencies.py`)  
   Blocked decisions are logged with policy and retry metadata, but there are no counters/histograms or near-limit telemetry.

12. **[PARTIALLY FIXED] Traffic-control 429 responses exist, but retry hint propagation is incomplete** (`backend/router.py`, `backend/services/rate_limit/dependencies.py`, `backend/app.py`)  
   Request-rate limiter now returns `429`, but `Retry-After` headers from raised `HTTPException` are currently not forwarded by the global HTTP exception handler.

13. **[NEW] Duplicate-cooldown default in code and env example are inconsistent** (`backend/config.py`, `backend/.env.example`)  
   Code default is `1s` while `.env.example` documents `45s`, which can silently weaken abuse protection if env vars are absent or misconfigured.
