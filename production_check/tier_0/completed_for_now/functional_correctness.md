# Production Concern: Functional Correctness (Tier 0)

Focus: whether the backend returns correct behavior/results for real user flows.

## Critical Functional Bugs

1. **[FIXED] Successful fact-check can end as `failed` due to notification error** (`backend/orchestrator.py`)  
   After result is saved, `NOTIFY` failure triggers global exception path and marks hunt failed, producing incorrect final status for a successful analysis.

2. **[FIXED] Hunts can be left in incorrect `processing` state when publish fails** (`backend/router.py`, `backend/orchestrator.py`)  
   Hunt transitions to `processing` before workflow publish; if publish fails, state says “processing” but no workflow is running.

3. **[FIXED] Completed hunts can become unreadable due to strict metadata requirement** (`backend/router.py`, `backend/schemas.py`)  
   Completed hunts now return with optional metadata fields, and missing `title/summary/trust_score` no longer triggers route-level runtime failure.

4. **[FIXED] One bad completed hunt can break `/hunts` list for the user** (`backend/router.py`)  
   List endpoint no longer performs hard metadata checks per completed hunt, so one record with missing metadata does not abort the entire response.

## High Severity

5. **[OPEN] User limit logic counts completed hunts as active** (`backend/db/database.py`, `backend/services/hunt_limits/hunt_limits.py`)  
   Users can get blocked with 429 after accumulating completed hunts, even with no current processing work.

6. **[OPEN] Message contract mismatch risk between API and response model** (`backend/router.py`, `backend/schemas.py`)  
   Endpoints declare `StartHuntResponse/HuntResponse` but on failure return ad-hoc `JSONResponse` shapes, which can break strict clients.

7. **[OPEN] `update_hunt_metadata` cannot clear fields and can preserve stale values** (`backend/db/database.py`)  
   Metadata only updates on truthy values, so empty-string/None updates are ignored and stale data can remain tied to hunts.

8. **[OPEN] Unknown worker step without RPC reply is silently dropped** (`backend/worker.py`)  
   For fire-and-forget tasks, unrecognized `step` logs error and returns without raising, potentially losing work with no corrective path.

9. **[OPEN] `url_fetcher` query normalization can crash on non-string query items** (`backend/services/url_fetcher/url_fetcher.py`)  
   `_normalize_queries` calls `.strip()` without type guard, so malformed model output can break URL-fetch stage.

## Important Correctness Gaps

10. **[OPEN] Claim row matching depends on exact claim text equality** (`backend/services/claim_verifier/claim_verifier.py`)  
   If verifier output slightly paraphrases claim text, rows are treated as unmatched and downgraded to generic `unverified`.

11. **[OPEN] Scrape failure path can produce structurally valid but evidence-empty outcomes** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`, `backend/services/rag_storage/rag_storage.py`)  
   Failed scrapes can collapse to empty context and eventually “no verdict/unverified” results without explicit hard-failure semantics.

12. **[FIXED] No explicit workflow-state reconciliation for stale jobs** (`backend/workflow_cleanup.py`, `backend/db/database.py`)  
   If a workflow stalls mid-chain, hunt status may remain functionally incorrect (`processing`) for long periods.

13. **[OPEN] Result payload correctness is weakly enforced at persistence boundary** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Any dict-shaped table can be serialized and stored; malformed logical content can still be treated as successful completion.
