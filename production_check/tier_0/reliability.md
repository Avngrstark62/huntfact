# Production Concern: Reliability (Tier 0)

Focus: automatic recovery, resilience to dependency failures, and consistency under faults.

## Release Blockers

1. **No effective retry strategy for critical external calls** (pipeline-wide)  
   OpenAI, AssemblyAI, Firecrawl, SearXNG, and notification calls mostly fail-fast with no bounded retry/backoff policy.

2. **No dead-letter / poison-message handling for task queues** (`backend/rmq/consumer.py`, `backend/worker.py`)  
   Repeatedly failing messages are not isolated into a DLQ path, so reliability degrades under bad payloads or flaky dependencies.

3. **No stale-job recovery mechanism** (`backend/router.py`, `backend/orchestrator.py`, `backend/db/database.py`)  
   Hunts can stay in `processing` indefinitely when workflows hang/fail mid-chain, with no automatic reconciliation.

4. **RPC task chain has no timeout budget by default** (`backend/orchestrator.py`, `backend/rmq/publisher.py`)  
   `publish_task_rpc` supports timeout but orchestration calls omit it, so one stuck step can block the whole workflow.

## High Severity

5. **Single-point dependency model in orchestration flow** (`backend/orchestrator.py`)  
   Most steps are hard-fail dependencies; a transient outage in one provider fails the whole job instead of degrading gracefully.

6. **Dual transcription requires both providers to succeed** (`backend/orchestrator.py`)  
   Workflow currently treats either transcriber failure as terminal, reducing completion reliability during provider incidents.

7. **Partial-success handling is not reliability-safe at terminal stage** (`backend/orchestrator.py`)  
   `NOTIFY` failure can invalidate an otherwise successful run by marking hunt `failed`, turning non-critical channel failure into data-level failure.

8. **Queue consumers re-raise processing errors** (`backend/rmq/consumer.py`)  
   Error propagation can terminate consumer loops, reducing system availability and causing delayed processing spikes after restart.

9. **No circuit-breaker behavior for repeatedly failing dependencies** (pipeline-wide)  
   System continues hammering failing external services instead of short-circuiting and recovering cleanly.

10. **No idempotency guardrails for workflow publication/execution** (`backend/router.py`, `backend/orchestrator.py`)  
   Retry/race scenarios can produce duplicate or inconsistent downstream work without explicit idempotency keys/state checks.

## Important Reliability Gaps

11. **Compensation logic is incomplete for mid-workflow failures** (`backend/orchestrator.py`)  
   Failures update status to `failed`, but no structured retry policy or staged resume exists for recoverable steps.

12. **Health model does not reflect end-to-end reliability** (`backend/health.py`, `backend/app.py`)  
   Health only considers DB/RabbitMQ, while core workflow dependencies can fail unnoticed, reducing operational reliability.

13. **Retry metadata exists but is unused** (`backend/rmq/schemas.py`)  
   `retry_count` is defined in task schema but not used to enforce retry limits, backoff, or terminal handling.

14. **User quota logic can create reliability perception issues** (`backend/db/database.py`)  
   Counting `completed` hunts as active causes persistent 429 behavior, perceived by users as service unreliability.

15. **Firecrawl failure path degrades silently** (`backend/services/firecrawl/firecrawl.py`, `backend/services/web_scraper/web_scraper.py`)  
   Returning empty content on scrape exceptions weakens reliability of final outputs without explicit hard failure classification.
