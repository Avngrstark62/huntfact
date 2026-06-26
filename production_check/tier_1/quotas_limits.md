# Production Concern: Quotas & Limits (Tier 1)

Focus: staying within internal and third-party service limits without causing cascading failures.

## Major Quotas & Limits Issues

1. **No explicit handling for provider quota/rate-limit responses (429/limit exhaustion)** (`backend/services/url_fetcher/url_fetcher.py`, `backend/llm.py`, `backend/services/transcriber/assemblyai.py`, `backend/services/rag_storage/rag_storage.py`)  
   External-limit failures are mostly surfaced as generic runtime errors, so quota exhaustion can abruptly fail user workflows instead of degrading gracefully.

2. **Internal user quota is narrow and not aligned to provider capacity** (`backend/router.py`, `backend/db/database.py`, `backend/db/models/user_hunt_limit.py`)  
   `hunts_limit` controls only active hunt count, not daily volume, per-minute burst, or provider-budget usage, so platform/provider limits can still be exceeded.

3. **No quota-aware throttling when dependencies approach limits** (backend-wide)  
   Backend does not reduce workload shape (query count, model usage, retries) based on near-limit provider conditions, increasing risk of broad outage during quota pressure.

4. **No per-provider quota telemetry or remaining-budget tracking** (backend-wide)  
   There is no persisted signal of quota consumption/remaining allowance for OpenAI, AssemblyAI, Firecrawl, SearXNG, or Firebase, making proactive limit management difficult.

## Important Quotas & Limits Gaps

5. **Hardcoded workload caps are static and not provider-plan aware** (`backend/services/url_fetcher/url_fetcher.py`, `backend/services/claim_verifier/claim_verifier.py`, `backend/services/rag_storage/rag_storage.py`)  
   Fixed limits (`max_results`, `MAX_QUERIES`, `MAX_CHUNKS_PER_QUERY`, chunking defaults) are not dynamically tuned to actual quota headroom.

6. **No operator-facing quota controls in runtime config** (`backend/config.py`)  
   Config lacks first-class settings for per-user/day quotas, provider call ceilings, and emergency limit tightening, reducing ability to respond during quota incidents.

7. **Quota failures are not clearly distinguished in user-visible failure states** (`backend/orchestrator.py`, `backend/db/database.py`, `backend/router.py`)  
   Quota exhaustion is folded into generic failed-job error flow, so users and operators cannot quickly identify “limit reached” vs other failure classes.
