# Production Concern: Validation

Focus: missing/weak validation across inputs, message contracts, config, and persisted data.

## Critical Validation Gaps

1. **No strict schema validation for task-queue messages** (`backend/worker.py`)  
   Worker processes raw `msg.get(...)` without `TaskMessage.model_validate`, so malformed task payloads are accepted until deep runtime failure.

2. **No strict schema validation for workflow payload shape beyond top-level model** (`backend/orchestrator.py`, `backend/rmq/schemas.py`)  
   `WorkflowMessage.payload` is `Dict[str, Any]`; required inner fields (`hunt_id`, `cdn_link`, `fcm_token`) are not strongly validated.

3. **No timeout/range constraints in message contract** (`backend/rmq/schemas.py`)  
   `priority` and `retry_count` have no bounds validation; invalid values can enter queue flow and produce undefined runtime behavior.

## High Validation Gaps

4. **`start-hunt` request lacks field-level constraints for user-critical inputs** (`backend/schemas.py`)  
   `fcm_token`, `caption`, `creator_handle`, `platform` have no min/max length, enum, or format constraints.

5. **`platform` is free text instead of enum** (`backend/schemas.py`)  
   Unexpected values are accepted and persisted, creating downstream inconsistency.

6. **Path parameter validation is too loose for hunt lookup** (`backend/router.py`)  
   `hunt_id` is only typed `int`; no positive-range guard prevents invalid IDs like `0`/negative values.

7. **URL fetcher validates list type but not item type** (`backend/services/url_fetcher/handler.py`, `backend/services/url_fetcher/url_fetcher.py`)  
   Non-string claim elements pass the handler and can break `.strip()` logic in service code.

8. **Claim extractor validates presence but not content type** (`backend/services/claim_extractor/handler.py`)  
   `content` can be non-string and still flow into logic expecting text.

9. **Translator handler validates presence but not type/size** (`backend/services/translator/handler.py`)  
   `transcript_text` can be non-string or huge without early rejection.

10. **Transcription-corrector handler does not validate `transcripts` shape** (`backend/services/transcription_corrector/handler.py`)  
   Missing strict `list[str]` validation allows malformed payloads to reach LLM merge logic.

11. **Save-result handler validates only `dict` presence, not table schema** (`backend/services/save_result_to_db/handler.py`)  
   Invalid row structures can pass and be persisted.

12. **Claim verifier handler validates list presence but not list item type/emptiness** (`backend/services/claim_verifier/handler.py`)  
   Mixed/empty claim arrays can pass and fail deeper.

13. **RAG storage handler validates `sources` as list but not per-source schema** (`backend/services/rag_storage/handler.py`)  
   Missing checks for required source fields (`url`, `content`) are deferred and inconsistently handled downstream.

## Medium Validation Gaps

14. **Config model lacks strong constraints for operational safety** (`backend/config.py`)  
   Many critical settings are plain strings/ints without URL format, numeric range, or non-empty enforcement.

15. **Auth config allows invalid production state at startup** (`backend/config.py`, `backend/auth/supabase_auth.py`)  
   JWKS/issuer/audience values can remain empty until request-time failure rather than fail-fast startup validation.

16. **DB write APIs accept unconstrained domain values** (`backend/db/database.py`)  
   `status`, `trust_score`, `title`, `summary` are not validated at boundary before persistence.

17. **Trust score in API response has no schema bounds** (`backend/schemas.py`)  
   Declared as `int | None` without `0..100` constraints.

18. **Response contracts do not enforce structured result payload** (`backend/schemas.py`)  
   `result` is a raw string; no schema validation guarantees result JSON structure for clients.

19. **API error responses can violate declared response models** (`backend/router.py`)  
   Endpoints declare typed `response_model`, but return ad-hoc `JSONResponse` bodies for failures without unified validation contract.

20. **Audio extractor URL validation is syntactic only** (`backend/services/audio_extractor/audio_extractor.py`)  
   Only scheme/netloc are checked; no stricter allowed-scheme/domain policy.
