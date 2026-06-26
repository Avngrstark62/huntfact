# Production Concern: Error Handling (Tier 0)

Focus: crash prevention, graceful failure behavior, and failure propagation quality.

## Release Blockers

1. **Notification-only failure can mark completed hunts as failed** (`backend/orchestrator.py`)  
   `NOTIFY` failure is handled in the same global exception path as core pipeline failures; this can overwrite successful fact-check outcomes with failed status.

2. **Consumer process can die on a single bad message** (`backend/rmq/consumer.py`)  
   Message processing exceptions are re-raised; one poison message can terminate task/workflow consumers and stop background processing.

3. **No poison-message isolation path** (`backend/rmq/consumer.py`, `backend/worker.py`)  
   Failed messages are not routed to dead-letter handling with explicit terminal classification; repeated failures can cause retry churn/outage behavior.

4. **Workflow publish failures leave inconsistent user-visible state** (`backend/router.py`)  
   Hunt is transitioned to `processing` before workflow publish; publish errors return 500 while the hunt may remain stuck in processing.

## High Severity

5. **Broad exception catch at API level collapses domain errors into generic 500** (`backend/router.py`)  
   Large `except Exception` blocks return generic internal error responses, hiding actionable failure classes from clients.

6. **Stack traces suppressed in production endpoint logs** (`backend/router.py`)  
   `exc_info=settings.app.debug` means traceback context is often missing when debug is false, reducing incident diagnosability.

7. **Database layer uses bare `except:` without structured context logging** (`backend/db/database.py`)  
   Multiple write paths rollback and re-raise but emit no operation-specific error logs.

8. **Error handling is inconsistent across handlers** (`backend/services/*/handler.py`)  
   Some handlers wrap service exceptions and return structured errors, while others let exceptions bubble; behavior differs by step and complicates reliable recovery.

9. **Internal exception strings are propagated as error payloads** (`backend/worker.py`, multiple handlers)  
   `str(e)` is returned in task error responses; can leak internal operational details and produce unstable client-facing error surfaces.

10. **Silent failure in Firecrawl path degrades quality without explicit error state** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`)  
   Scrape exceptions can be converted to empty output and continued flow, masking true failure source.

## Important Gaps

11. **Startup dependency initialization failures are tolerated without hard fail policy** (`backend/app.py`)  
   App continues boot with partial dependency failures; errors are logged, but no strict readiness gate enforces fail-fast behavior for critical dependencies.

12. **Firebase init failures are deferred and recur later at notify time** (`backend/firebase_config.py`, `backend/services/notification_sender/notification_sender.py`)  
   Initialization errors do not stop service startup, causing delayed user-facing failures during notification sending.

13. **Workflow-level parse/validation failures may not mark hunt status** (`backend/orchestrator.py`)  
   If failure occurs before reliable hunt context extraction, hunt failure state may not be updated consistently.

14. **Error taxonomy is not standardized across pipeline steps** (pipeline-wide)  
   Similar failures are represented with different message formats and semantics (`error`, `RuntimeError`, generic 500), making automated handling brittle.

15. **Catch-and-continue behavior lacks explicit compensation strategy** (`backend/services/web_scraper/web_scraper.py`)  
   Skipped URLs and suppressed scrape errors are not translated into deterministic compensation logic or user-visible partial-failure signaling.
