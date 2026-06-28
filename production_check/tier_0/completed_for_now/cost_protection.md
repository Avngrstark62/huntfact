# Production Concern: Cost Protection (Tier 0)

Focus: preventing unbounded provider spend per request, per user, and during failure modes.

## Release Blockers

1. **[OPEN] No explicit per-request cost budget / execution cap** (pipeline-wide)  
   A single hunt can trigger many paid calls (dual transcription, multiple LLM calls, embeddings, scrape/search) with no hard budget cutoff.

2. **[OPEN] No per-user spend controls beyond active-hunt count** (`backend/router.py`, `backend/db/database.py`)  
   `hunts_limit` caps active records, not token/API spend, daily budget, or burst cost.

3. **[OPEN] Dual-transcriber design doubles transcription cost by default** (`backend/orchestrator.py`)  
   Both OpenAI and AssemblyAI transcription are always invoked in parallel for every run.

4. **[OPEN] No token/input size ceiling for LLM stages** (`backend/services/*` using `llm.call_with_schema`)  
   Very large transcript/context payloads can produce unexpectedly high token bills.

## High Severity

5. **[OPEN] RAG embedding volume is effectively unbounded per hunt** (`backend/services/rag_storage/rag_storage.py`)  
   Chunking can create large document counts with no max chunks/source limit before paid embedding generation.

6. **[OPEN] Claim verification retrieval fanout can be expensive at scale** (`backend/services/claim_verifier/claim_verifier.py`)  
   Up to `MAX_QUERIES=10` embedding lookups and up to `MAX_CHUNKS_PER_QUERY=5` retrieval context per hunt can inflate downstream LLM context cost.

7. **[OPEN] Web search + scraping fanout has weak cost guardrails** (`backend/services/url_fetcher/url_fetcher.py`, `backend/services/web_scraper/web_scraper.py`)  
   Query generation can produce up to 10 searches and URL selection can feed multiple scrape calls without budget-aware stopping.

8. **[OPEN] No retry cost guardrails if retry logic is added later** (pipeline-wide)  
   Current architecture lacks attempt-cost accounting; introducing retries without budget tracking can quickly multiply spend.

9. **[OPEN] No provider quota-awareness or rate-based cost throttling** (OpenAI/AssemblyAI/Firecrawl/SearXNG/Firebase paths)  
   System does not adapt behavior when nearing plan limits or high-burn periods.

10. **[NEW] Cluster fanout executes full verification loops in parallel without concurrency budget** (`backend/orchestrator.py`)  
   Each extracted cluster triggers URL fetch/search/scrape/embedding/LLM verification concurrently via `asyncio.gather(...)`, allowing burst spend when cluster count is high.

## Important Gaps

11. **[OPEN] No cost telemetry persisted for hunts** (backend-wide)  
   Token/API usage is not stored per hunt/user, so expensive patterns cannot be detected or controlled.

12. **[OPEN] LLM usage logging exists but is debug-gated and not policy-enforced** (`backend/llm.py`)  
   Usage is logged only when `LLM_DEBUG` is enabled; this is observability, not active spend protection.

13. **[OPEN] Repeated failed hunts can be retriggered without cooldown** (`backend/router.py`)  
   Failed hunts are immediately retried via status transition path, with no explicit cooldown/backoff budget to limit repeated spend on bad inputs.

14. **[OPEN] No request-level mode switching for cheaper fallback paths** (pipeline-wide)  
   There is no dynamic downgrade path (e.g., skip expensive enrichment/secondary models) under high-cost conditions.

15. **[NEW] Metadata generation adds an extra reasoning-model LLM call per successful hunt** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Title/summary generation is always invoked with `settings.llm.reasoning_model`, adding avoidable marginal spend without budget checks.

16. **[NEW] Core OpenAI wrapper/embedding calls have no explicit timeout guardrails** (`backend/llm.py`, `backend/services/embeddings/embeddings.py`, `backend/services/rag_storage/rag_storage.py`)  
   Missing request timeouts increase risk of long-running or hanging paid calls that inflate per-hunt cost unpredictably.
