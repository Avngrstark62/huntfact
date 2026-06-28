# Production Concern: Privacy (Tier 0)

Focus: user/content data minimization, exposure, retention, and third-party sharing controls.

## Release Blockers

1. **[FIXED] Sensitive device token is logged in plaintext** (`backend/services/notification_sender/notification_sender.py`)  
   `fcm_token` is personally linkable device-routing data and is currently emitted directly to logs.

2. **[FIXED] User-generated content is logged at runtime** (`backend/orchestrator.py`)  
   Pipeline logs include full/large objects like translated transcript and extracted claim structures, exposing user content in log systems.

3. **[FIXED] User identity + content linkage in logs** (`backend/router.py`)  
   Logs join `user_id` with user-submitted media links (`video_link`, `cdn_link`), increasing re-identification risk from observability data.

## High Severity

4. **[OPEN] No explicit data-retention policy for core user content in DB** (`backend/db/models/hunt.py`, `backend/db/database.py`)  
   Fact-check results, captions, creator handles, and media links are stored without TTL/retention controls.

5. **[OPEN] No user-data deletion/erasure flow visible in backend API** (`backend/router.py`, `backend/db/database.py`)  
   There is no endpoint/workflow for deleting a user's stored hunts/content associations.

6. **[OPEN] Raw content is sent to multiple third parties without privacy guardrails** (pipeline-wide: OpenAI, AssemblyAI, Firecrawl, SearXNG, Firebase)  
   Transcripts/claims/page content and notification identifiers are transmitted externally without code-level minimization/redaction boundaries.

7. **[OPEN] No redaction or minimization before LLM/provider calls** (`backend/services/*` using LLM/transcriber/search/scrape)  
   Potentially sensitive text passes through unchanged, including personal or incidental private details from source media.

8. **[OPEN] No explicit segregation of logs by sensitivity** (logging-wide)  
   Operational logs mix system and user-content data, increasing blast radius for log access breaches.

9. **[NEW] Failure paths can persist and log user-linked payload fragments** (`backend/orchestrator.py`, `backend/db/database.py`)  
   Error handling stores raw failure text in hunt records and logs truncated workflow body fragments, which may include links, identifiers, and user-content snippets.

## Important Privacy Gaps

10. **[OPEN] `result` payload persistence may capture sensitive personal claims indefinitely** (`backend/services/save_result_to_db/save_result_to_db.py`, `backend/db/models/hunt.py`)  
   Stored result tables can include sensitive assertions and source links tied to user hunt history.

11. **[OPEN] Queue payloads carry user-linked identifiers across infrastructure** (`backend/router.py`, `backend/orchestrator.py`, `backend/worker.py`)  
   `fcm_token`, hunt identifiers, and content-derived artifacts flow through RMQ payloads without privacy tagging/redaction policy.

12. **[OPEN] Auth logs include persistent user identifiers** (`backend/auth/supabase_auth.py`)  
   Successful auth logs include `user_id` at endpoint level; acceptable for ops, but currently lacks privacy-mode controls.

13. **[OPEN] No visible consent/notice enforcement boundary for external processing** (backend API layer)  
   Code does not enforce or check per-request consent flags for sending media-derived content to external AI/search/scraping providers.
