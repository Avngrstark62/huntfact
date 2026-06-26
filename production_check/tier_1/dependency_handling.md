# Production Concern: Dependency Handling (Tier 1)

Focus: resilience to third-party provider failures, behavior changes, and SDK/API contract drift.

## Major Dependency Handling Issues

1. **No fallback providers for critical external steps** (`backend/services/url_fetcher/url_fetcher.py`, `backend/services/firecrawl/firecrawl.py`, `backend/llm.py`, `backend/services/transcriber/*.py`)  
   Search, scrape, LLM, and transcription each rely on a primary provider path; when a provider degrades or changes behavior, workflow reliability drops sharply.

2. **Provider failures are inconsistently classified and recovered** (`backend/services/firecrawl/firecrawl.py`, `backend/services/url_fetcher/url_fetcher.py`, `backend/services/transcriber/assemblyai.py`)  
   Some failures are raised, others are converted to empty outputs, creating uneven dependency-failure handling and unpredictable downstream behavior.

3. **Weak response-contract validation for third-party payloads** (`backend/services/transcriber/assemblyai.py`, `backend/services/firecrawl/firecrawl.py`)  
   Code accesses provider fields like `upload_url`, `id`, and `markdown` with minimal schema checks, so provider response shape changes can break runtime unexpectedly.

4. **No model/provider fallback in LLM wrapper** (`backend/llm.py`, `backend/config.py`)  
   LLM calls use one configured model per path without automatic downgrade/fallback model routing when provider/model availability changes.

## Important Dependency Handling Gaps

5. **Startup tolerates optional dependency init failures without operational gating** (`backend/app.py`, `backend/firebase_config.py`)  
   Firebase/Chroma init failures are logged but app continues, so dependency outages can surface later as user-facing runtime failures.

6. **JWKS key-rotation handling can lag for auth failures** (`backend/auth/supabase_auth.py`)  
   JWKS is cached by TTL; during upstream key rotation, valid tokens may fail until cache refresh, increasing avoidable authentication outages.

7. **Dependency version policy is broad (`>=`) and vulnerable to upgrade drift** (`backend/pyproject.toml`)  
   Wide version ranges increase risk that upstream package updates introduce behavior changes unless lockfile discipline is strictly enforced in all deploy environments.
