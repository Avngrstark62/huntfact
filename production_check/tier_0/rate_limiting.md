# Production Concern: Rate Limiting (Tier 0)

Focus: abuse prevention and load control at API, queue, and expensive downstream boundaries.

## Release Blockers

1. **No API request rate limiting at all (IP/user/token level)** (`backend/router.py`, `backend/app.py`)  
   Endpoints have no per-second/minute throttling controls; bot/abuse traffic can flood the service.

2. **No brute-force/abuse protection on public endpoints** (`backend/router.py`)  
   `/start-hunt` and `/health` can be hit unboundedly, enabling denial-of-service and cost-amplification attacks.

3. **No downstream provider call-rate guards** (pipeline-wide)  
   OpenAI/AssemblyAI/Firecrawl/SearXNG/Firebase calls are not protected by token-bucket/leaky-bucket style limits.

## High Severity

4. **Current `hunts_limit` is concurrency-like quota, not true rate limit** (`backend/router.py`, `backend/db/database.py`)  
   It caps active hunts per user but does not limit request frequency, burst behavior, or repeated retries in short intervals.

5. **No per-user/per-IP burst control for expensive workflow trigger** (`backend/router.py`)  
   A user can rapidly call `/start-hunt` until quota checks race or queue pressure builds.

6. **No queue ingress throttling or producer backpressure policy** (`backend/rmq/publisher.py`, `backend/orchestrator.py`)  
   Task/workflow publish paths do not enforce throughput caps when downstream workers are saturated.

7. **No route-level distinction between cheap and expensive limits** (`backend/router.py`)  
   Same open behavior for read endpoints and costly write/orchestration endpoints increases abuse surface.

## Important Gaps

8. **No adaptive limiting based on dependency health** (pipeline-wide)  
   During upstream degradation, the system does not tighten acceptance rate to protect stability.

9. **No account-tier/role aware limits** (`backend/db/models/user_hunt_limit.py`, `backend/db/database.py`)  
   Single static default limit (`30`) lacks nuanced controls (burst, daily quota, cooldown).

10. **No idempotency key + dedupe guard for repeated identical requests** (`backend/router.py`, `backend/db/database.py`)  
   Repeated submissions of same action still consume API/queue resources before dedupe effects stabilize.

11. **No observability for limit decisions** (backend-wide)  
   There are no metrics/log standards for rate-limit hits, near-limit events, or per-principal abuse patterns.

12. **429 semantics are quota-specific, not traffic-control specific** (`backend/router.py`)  
   Returned `429` reflects active-hunt quota logic, not standardized request-rate policy with retry hints/windows.
