# Production Concern: Error Handling (Tier 0)

Focus: crash prevention, graceful failure behavior, and failure propagation quality.

## Release Blockers

1. **[FIXED] Notification-only failure can mark completed hunts as failed** (`backend/orchestrator.py`)  
   `NOTIFY` runs after the critical save path in an isolated non-critical block; notification failure no longer flips completed hunts to failed.

2. **[FIXED] Consumer process can die on a single bad message** (`backend/rmq/consumer.py`)  
   Per-message exceptions are quarantined and consumed safely, while consumer-level failures reconnect instead of terminating processing.

3. **[FIXED] No poison-message isolation path** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/rmq/publisher.py`, `backend/config.py`)  
   Consumers classify terminal failures (`invalid_json`, schema validation failure, handler exception), quarantine messages with error metadata, and ack/reject safely.

4. **[FIXED] Workflow publish failures leave inconsistent user-visible state** (`backend/router.py`, `backend/services/workflow_admission/workflow_admission.py`, `backend/workflow_cleanup.py`)  
   Admission/publish now uses automatic retries to absorb transient failures, and cleanup marks long-stale queued/processing hunts failed and clears admissions, preventing long-lived queue-state/DB-state divergence in practice.

5. **[FIXED] Duplicate admission response semantics are now intentional and consistent** (`backend/services/workflow_admission/workflow_admission.py`)  
   Duplicate admission now returns a clear success response (`"Hunt is already processing."`) by design, while retry-exhausted unexpected errors return failure (`"Hunt failed previously. Please try again."`), avoiding mixed duplicate/error signaling.

6. **[FIXED] Start-hunt API no longer returns stale status payload** (`backend/router.py`, `backend/schemas.py`)  
   `/start-hunt` response contract is now minimal (`success`, `message`, `hunt_id`) and no longer returns status/result metadata that could become stale during admission/publish flow.

## High Severity

7. **[OPEN] Broad exception catch at API level collapses domain errors into generic 500** (`backend/router.py`)  
   Large `except Exception` blocks return generic internal error responses, hiding actionable failure classes from clients.

8. **[OPEN] Stack traces suppressed in production endpoint logs** (`backend/router.py`)  
   `exc_info=settings.app.debug` means traceback context is often missing when debug is false, reducing incident diagnosability.

9. **[OPEN] Database layer uses bare `except:` without structured context logging** (`backend/db/database.py`)  
   Multiple write paths rollback and re-raise but emit no operation-specific error logs.

10. **[OPEN] Error handling is inconsistent across handlers** (`backend/services/*/handler.py`)  
   Some handlers wrap service exceptions and return structured errors, while others let exceptions bubble; behavior differs by step and complicates reliable recovery.

11. **[OPEN] Internal exception strings are propagated as error payloads** (`backend/worker.py`, multiple handlers)  
   `str(e)` is returned in task error responses; can leak internal operational details and produce unstable client-facing error surfaces.

12. **[OPEN] Silent failure in Firecrawl path degrades quality without explicit error state** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`)  
   Scrape exceptions are converted to empty output and continued flow, with exception logging effectively suppressed at call site.

## Important Gaps

13. **[OPEN] Startup dependency initialization failures are tolerated without hard fail policy** (`backend/app.py`)  
   App continues boot with partial dependency failures; errors are logged, but no strict readiness gate enforces fail-fast behavior for critical dependencies.

14. **[OPEN] Firebase init failures are deferred and recur later at notify time** (`backend/firebase_config.py`, `backend/services/notification_sender/notification_sender.py`)  
   Initialization errors do not stop service startup, causing delayed user-facing failures during notification sending.

15. **[OPEN] Workflow-level parse/validation failures may not mark hunt status** (`backend/orchestrator.py`)  
   If failure occurs before reliable hunt context extraction, hunt failure state may not be updated consistently.

16. **[OPEN] Error taxonomy is not standardized across pipeline steps** (pipeline-wide)  
   Similar failures are represented with different message formats and semantics (`error`, `RuntimeError`, generic 500), making automated handling brittle.

17. **[OPEN] Catch-and-continue behavior lacks explicit compensation strategy** (`backend/services/web_scraper/web_scraper.py`)  
   Skipped URLs and suppressed scrape errors are not translated into deterministic compensation logic or user-visible partial-failure signaling.
