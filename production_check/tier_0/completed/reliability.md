# Production Concern: Reliability (Tier 0)

Focus: automatic recovery, resilience to dependency failures, and consistency under faults.

## Release Blockers

1. **[FIXED] No dead-letter / poison-message handling for task queues** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/config.py`)  
   Consumers now quarantine invalid/poison messages with reason metadata into dead-letter queues and continue processing healthy traffic.

2. **[FIXED] No stale-job recovery mechanism** (`backend/workflow_cleanup.py`, `backend/db/database.py`, `backend/config.py`)  
   Periodic cleanup now marks stale `processing` and `queued` hunts as failed and clears failed admissions to reconcile stalled workflows.

## High Severity

3. **[OPEN] Single-point dependency model in orchestration flow** (`backend/orchestrator.py`)  
   Most steps are hard-fail dependencies; a transient outage in one provider fails the whole job instead of degrading gracefully.

4. **[OPEN] Dual transcription requires both providers to succeed** (`backend/orchestrator.py`)  
   Workflow currently treats either transcriber failure as terminal, reducing completion reliability during provider incidents.

5. **[FIXED] Partial-success handling is not reliability-safe at terminal stage** (`backend/orchestrator.py`)  
   `NOTIFY` now runs in isolated non-critical flow after persistence; notification failure no longer flips successful hunts to `failed`.

6. **[FIXED] Queue consumers re-raise processing errors** (`backend/rmq/consumer.py`)  
   Per-message processing errors are handled/quarantined without terminating consume loops, and top-level failures reconnect automatically.

7. **[OPEN] No circuit-breaker behavior for repeatedly failing dependencies** (pipeline-wide)  
   System continues hammering failing external services instead of short-circuiting and recovering cleanly.

8. **[OPEN] No idempotency guardrails for workflow publication/execution** (`backend/router.py`, `backend/orchestrator.py`)  
   Retry/race scenarios can produce duplicate or inconsistent downstream work without explicit idempotency keys/state checks.

## Important Reliability Gaps

9. **[OPEN] Compensation logic is incomplete for mid-workflow failures** (`backend/orchestrator.py`)  
   Failures update status to `failed`, but no structured retry policy or staged resume exists for recoverable steps.

10. **[OPEN] Health model does not reflect end-to-end reliability** (`backend/health.py`, `backend/app.py`)  
   Health only considers DB/RabbitMQ, while core workflow dependencies can fail unnoticed, reducing operational reliability.

11. **[OPEN] Retry metadata exists but is unused** (`backend/rmq/schemas.py`)  
   `retry_count` is defined in task schema but not used to enforce retry limits, backoff, or terminal handling.

12. **[OPEN] User quota logic can create reliability perception issues** (`backend/db/database.py`)  
   Counting `completed` hunts as active causes persistent 429 behavior, perceived by users as service unreliability.

13. **[OPEN] Firecrawl failure path degrades silently** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`)  
   Returning empty content on scrape exceptions weakens reliability of final outputs without explicit hard failure classification.
