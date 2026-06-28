# Production Concern: User Experience (Tier 1)

Focus: backend response behavior that affects user trust during loading, completion, and failure states.

## Major User Experience Issues

1. **Long-running hunts expose only a coarse `processing` state** (`backend/router.py`, `backend/orchestrator.py`)  
   Users cannot see meaningful progress (transcribing/verifying/saving), so long waits feel stuck and increase drop-off/retry spam.

2. **Most unexpected API failures collapse to generic `Internal Server Error`** (`backend/router.py`)  
   Clients get little actionable context for recovery, which makes real failures look random and reduces trust.

3. **Completed result retrieval can fail hard if metadata is missing** (`backend/router.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   Backend enforces title/summary/trust metadata before serving completed hunts; partial-save scenarios can surface as 500 instead of a degraded-but-usable response.

4. **No user-facing distinction between transient and final failures** (`backend/orchestrator.py`, `backend/db/database.py`, `backend/router.py`)  
   Failed hunts return one `failed` status path, so users cannot tell whether retry is likely to work or whether input should be changed.

## Important User Experience Gaps

5. **`start-hunt` success messaging is static across materially different states** (`backend/router.py`)  
   Response message remains “Hunt started successfully” for already-completed, already-processing, retry, and new runs, which can confuse user expectations.

6. **Error response contracts are inconsistent across endpoints** (`backend/router.py`, `backend/schemas.py`)  
   Success paths use typed models, but many errors return ad-hoc `detail` JSON, increasing client-side ambiguity and uneven UX handling.

7. **Failure details are stored as raw pipeline error text** (`backend/orchestrator.py`, `backend/db/database.py`, `backend/schemas.py`)  
   Technical internal error strings can surface in hunt responses, creating noisy or confusing user-facing failure explanations.
