# Production Concern: Caching (Tier 1)

Focus: whether backend reuses expensive work safely to reduce latency/cost without serving stale or incorrect results.

## Major Caching Issues

1. **Only coarse final-result reuse exists; no caching for expensive intermediate steps** (`backend/router.py`, `backend/services/url_fetcher/url_fetcher.py`, `backend/services/web_scraper/web_scraper.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   Pipeline reuses completed hunts by exact `video_link`, but search/scrape/LLM/retrieval stages are recomputed on new inputs and retries, leaving major avoidable latency/cost.

2. **No TTL/refresh policy for reused completed hunt results** (`backend/router.py`, `backend/db/database.py`)  
   Cached-by-record completed results can be served indefinitely with no freshness window, so stale verdicts may persist after source changes or model updates.

3. **Cache key quality is weak for result reuse** (`backend/router.py`, `backend/db/database.py`)  
   Reuse key is raw `video_link` equality; URL variants for the same media bypass reuse, while exact-match reuse may conflate contexts where metadata/caption changed.

4. **No provider-response cache for high-cost external calls** (`backend/services/url_fetcher/url_fetcher.py`, `backend/services/firecrawl/firecrawl.py`, `backend/llm.py`)  
   Repeated calls to SearXNG/Firecrawl/OpenAI are always live, so identical or near-identical requests repeatedly pay full latency and cost.

## Important Caching Gaps

5. **No negative caching for repeated failure cases** (`backend/services/url_fetcher/url_fetcher.py`, `backend/services/firecrawl/firecrawl.py`)  
   Known failing queries/URLs are retried from scratch each run, increasing failure amplification and unnecessary external traffic.

6. **No explicit cache observability (hit/miss/stale rates)** (backend-wide)  
   Without cache effectiveness metrics, it is hard to detect poor keying, stale-result risk, or regressions in reuse behavior.

7. **No configuration surface for cache policy controls** (`backend/config.py`)  
   There are no backend settings for cache TTL/size/invalidation strategy, making safe operational tuning impossible as traffic patterns change.
