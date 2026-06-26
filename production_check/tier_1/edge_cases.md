# Production Concern: Edge Cases

Focus: empty, huge, malformed, and unexpected inputs that can break or annoy users.

## Critical Edge Cases

1. **Notification failure can flip a successful hunt to failed** (`backend/orchestrator.py`)  
   After result is saved, any `NOTIFY` error enters global exception flow and marks hunt `failed`; users may lose a valid completed result due to notification-only issues.

2. **No timeout on RPC chain leads to indefinite processing** (`backend/orchestrator.py`, `backend/rmq/publisher.py`)  
   If any step hangs, hunt can remain stuck forever in `processing`, creating user-facing "never completes" behavior.

3. **AssemblyAI polling is unbounded** (`backend/services/transcriber/assemblyai.py`)  
   Poll loop has no max attempts and HTTP calls have no timeout; malformed/slow upstream responses can hang worker execution.

## High Edge Cases

4. **Malformed claims list entries can crash URL fetch step** (`backend/services/url_fetcher/url_fetcher.py`)  
   Non-string claim items trigger `.strip()` failures, causing full step failure instead of skipping bad items.

5. **Transcription corrector accepts wrong payload shape** (`backend/services/transcription_corrector/handler.py`, `backend/services/transcription_corrector/transcription_corrector.py`)  
   `transcripts` is not type-checked as `list[str]`; unexpected types (string/object/mixed list) can produce broken merge behavior or exceptions.

6. **Invalid/blank `fcm_token` is accepted at API boundary** (`backend/schemas.py`, `backend/router.py`)  
   Token is required but unconstrained; empty/garbage token passes request validation and fails later in background, degrading UX with late-stage failures.

7. **No stale-hunt recovery for long-running edge failures** (`backend/router.py`, `backend/orchestrator.py`)  
   There is no reaper/timeout-based state transition for old `processing` hunts; transient edge failures leave permanent limbo states.

8. **Exact-string URL dedupe misses semantically same links** (`backend/db/database.py`, `backend/db/models/hunt.py`)  
   Small URL variants (query params, trailing slash, short-link forms) create duplicate hunts and inconsistent user history.

## Medium Edge Cases

9. **Huge transcript/content inputs have no hard caps** (`backend/services/translator/translator.py`, `backend/services/claim_extractor/claim_extractor.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   Very large text can overflow model context, increase latency, and fail unpredictably instead of being truncated/rejected early.

10. **Huge scraped context can explode embedding/storage cost** (`backend/services/rag_storage/rag_storage.py`)  
   No source/chunk upper bound before embedding and insert; unusually large pages can cause memory spikes and slowdowns.

11. **Base64 decode is permissive for malformed audio payloads** (`backend/services/transcriber/handler.py`)  
   Decode path does not enforce strict validation; corrupted payloads can pass decode and fail deeper with less actionable errors.

12. **Metadata strictness can break reads for partially completed hunts** (`backend/router.py`)  
   Completed hunts missing title/summary/trust score raise runtime errors, so users may get 500 instead of degraded-but-readable response.

13. **Health check misses non-DB/RMQ dependency edge failures** (`backend/health.py`, `backend/app.py`)  
   Service may report healthy while LLM/scraping/vector dependencies are unavailable, causing confusing user-visible failures.

14. **`platform` input has no enum/constraint** (`backend/schemas.py`)  
   Unexpected platform values are stored and propagated, increasing downstream branching bugs and inconsistent analytics.
