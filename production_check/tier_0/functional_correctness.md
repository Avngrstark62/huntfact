# Production Concern: Functional Correctness (Tier 0)

Focus: whether the backend returns correct behavior/results for real user flows.

## Critical Functional Bugs

1. **Successful fact-check can end as `failed` due to notification error** (`backend/orchestrator.py`)  
   After result is saved, `NOTIFY` failure triggers global exception path and marks hunt failed, producing incorrect final status for a successful analysis.

2. **Hunts can be left in incorrect `processing` state when publish fails** (`backend/router.py`)  
   Hunt transitions to `processing` before workflow publish; if publish fails, state says “processing” but no workflow is running.

3. **Completed hunts can become unreadable due to strict metadata requirement** (`backend/router.py`)  
   `_require_hunt_metadata` raises runtime errors if `title/summary/trust_score` missing, causing 500 for otherwise valid completed hunts.

4. **One bad completed hunt can break `/hunts` list for the user** (`backend/router.py`)  
   In list endpoint, metadata check failure for one hunt aborts the entire response instead of isolating that record.

## High Severity

5. **User limit logic counts completed hunts as active** (`backend/db/database.py`, `backend/router.py`)  
   Users can get blocked with 429 after accumulating completed hunts, even with no current processing work.

6. **Message contract mismatch risk between API and response model** (`backend/router.py`, `backend/schemas.py`)  
   Endpoints declare `StartHuntResponse/HuntResponse` but on failure return ad-hoc `JSONResponse` shapes, which can break strict clients.

7. **`update_hunt_metadata` cannot clear fields and can preserve stale values** (`backend/db/database.py`)  
   Metadata only updates on truthy values, so empty-string/None updates are ignored and stale data can remain tied to hunts.

8. **Unknown worker step without RPC reply is silently dropped** (`backend/worker.py`)  
   For fire-and-forget tasks, unrecognized `step` logs error and returns without raising, potentially losing work with no corrective path.

9. **`url_fetcher` query normalization can crash on non-string query items** (`backend/services/url_fetcher/url_fetcher.py`)  
   `_normalize_queries` calls `.strip()` without type guard, so malformed model output can break URL-fetch stage.

## Important Correctness Gaps

10. **Claim row matching depends on exact claim text equality** (`backend/services/claim_verifier/claim_verifier.py`)  
   If verifier output slightly paraphrases claim text, rows are treated as unmatched and downgraded to generic `unverified`.

11. **Scrape failure path can produce structurally valid but evidence-empty outcomes** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`, `backend/services/rag_storage/rag_storage.py`)  
   Failed scrapes can collapse to empty context and eventually “no verdict/unverified” results without explicit hard-failure semantics.

12. **No explicit workflow-state reconciliation for stale jobs** (`backend/router.py`, `backend/orchestrator.py`)  
   If a workflow stalls mid-chain, hunt status may remain functionally incorrect (`processing`) for long periods.

13. **Result payload correctness is weakly enforced at persistence boundary** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Any dict-shaped table can be serialized and stored; malformed logical content can still be treated as successful completion.
