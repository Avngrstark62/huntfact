# Production Concern: Output Validation (Tier 0)

Focus: validating outputs from LLMs/services before they are consumed, persisted, or returned.

## Release Blockers

1. **[FIXED] Core result payload is stored as opaque string, not validated structured JSON** (`backend/services/save_result_to_db/save_result_to_db.py`, `backend/db/models/hunt.py`, `backend/schemas.py`)  
   The fact-check table is serialized and persisted as string without schema enforcement at persistence/read boundaries.

2. **[FIXED] No strict schema validation for worker step outputs before orchestration use** (`backend/worker.py`, `backend/orchestrator.py`, `backend/rmq/schemas.py`, `backend/rmq/publisher.py`)  
   Worker success payloads and orchestrator-consumed RPC outputs are now validated against step-specific schemas and typed RPC envelopes before downstream use.

3. **[FIXED] No enforced output schema at API boundary for error paths** (`backend/router.py`, `backend/app.py`, `backend/schemas.py`)  
   Router now raises typed HTTP exceptions and global FastAPI exception handlers normalize error payloads into a consistent `ErrorResponse` shape.

4. **[FIXED] Orchestrator accepts loosely shaped "success" step payloads without strict result contract checks** (`backend/orchestrator.py`, `backend/rmq/schemas.py`, `backend/rmq/publisher.py`)  
   `_run_rpc_step` now enforces typed RPC envelope parsing, step-match validation, and step-specific `result` schema checks before returning success payloads.

## High Severity

5. **[OPEN] LLM outputs are schema-checked, but semantic post-validation is weak** (`backend/services/claim_verifier/claim_verifier.py`, `backend/services/claim_extractor/claim_extractor.py`, `backend/services/web_scraper/web_scraper.py`)  
   Structural Pydantic validation exists, but important semantic checks (source quality sufficiency, claim coverage completeness, contradiction sanity) are not strictly enforced.

6. **[OPEN] `trust_score` output is computed from loosely typed row confidence values** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Confidence coercion falls back/clamps rather than rejecting malformed rows, allowing low-quality upstream output to silently shape final trust score.

7. **[FIXED] Completed-hunt response depends on strict metadata presence and can hard-fail** (`backend/router.py`, `backend/schemas.py`)  
   Hunt response metadata fields are now optional and responses degrade gracefully when metadata is missing, avoiding strict runtime hard-fail behavior.

8. **[OPEN] No schema versioning for persisted result format** (`backend/services/save_result_to_db/save_result_to_db.py`, DB `result` field)  
   Changes in table shape can break consumers because persisted output has no version marker/migration guard.

9. **[OPEN] Queue message payload contracts are shallow (`Dict[str, Any]`)** (`backend/rmq/schemas.py`)  
   Message-level typing validates envelope fields but not step-specific output payload shape, allowing invalid intermediate outputs to propagate.

## Important Gaps

10. **[OPEN] Handler return contracts are implicit and inconsistent** (`backend/services/*/handler.py`)  
   Handlers return dicts with varying keys (`results`, `context`, `table`, `saved`, etc.) without centralized schema validation layer.

11. **[OPEN] Web scrape output can silently drop failed sources without quality threshold checks** (`backend/services/web_scraper/web_scraper.py`)  
   Failed scrape candidates are skipped; output may be technically valid but evidentially insufficient without explicit minimum-quality gates.

12. **[OPEN] RAG retrieval output accepts partial/missing metadata with permissive fallback logic** (`backend/services/claim_verifier/claim_verifier.py`)  
   Missing document metadata is tolerated and normalized, which can hide retrieval integrity issues instead of failing early.

13. **[OPEN] No end-to-end output conformance test at runtime** (pipeline-wide)  
   There is no final gate validating that produced hunt output is both schema-correct and user-safe before marking hunt completed.

14. **[NEW] Handler-level output contract is inconsistent for invalid input paths** (`backend/services/audio_extractor/handler.py`, `backend/services/*/handler.py`)  
   Example: `handle_extract_audio` returns `None` for missing payload fields while other handlers return structured error dicts, weakening predictable output validation behavior across steps.
