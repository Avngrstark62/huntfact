# Production Concern: Retry Strategy (Tier 0)

Focus: automatic recovery from transient failures without causing retry storms or silent drops.

## Release Blockers

1. **No unified retry policy for external providers** (pipeline-wide)  
   OpenAI, AssemblyAI, Firecrawl, SearXNG, and Firebase paths are mostly fail-fast; transient network/provider errors are not retried with bounded policy.

2. **Task retry metadata exists but is unused** (`backend/rmq/schemas.py`, `backend/worker.py`, `backend/rmq/consumer.py`)  
   `retry_count` is defined in queue schema but no logic increments/checks it, so retry governance is effectively absent.

3. **No dead-letter / terminal-failure channel for exhausted retries** (`backend/rmq/*`)  
   There is no explicit DLQ strategy for permanently failing messages after retry attempts.

4. **No backoff + jitter strategy** (backend-wide)  
   Failures are retried ad hoc (or not retried at all); there is no exponential backoff with jitter to prevent synchronized failure bursts.

## High Severity

5. **Orchestrator step failures abort workflow immediately without selective retry** (`backend/orchestrator.py`)  
   Every failed RPC step raises terminal error instead of retrying only transient classes (timeouts, 5xx, connection resets).

6. **AssemblyAI polling is repetition without retry classification** (`backend/services/transcriber/assemblyai.py`)  
   Loop keeps polling status, but request failures are treated as exceptions, not as controlled retry states with limits.

7. **SearXNG query failure kills entire URL fetch step** (`backend/services/url_fetcher/url_fetcher.py`)  
   Single query failure raises runtime error for the full step; no per-query retry/fallback window.

8. **Notification send has no retry path** (`backend/services/notification_sender/notification_sender.py`, `backend/orchestrator.py`)  
   One transient FCM failure can mark workflow failed; no delayed retry queue or outbox-like retry mechanism.

9. **No DB write retry handling for transient DB faults** (`backend/db/database.py`)  
   Write operations rollback and raise immediately without bounded retry for retry-safe transient DB errors.

## Important Gaps

10. **Retryability is not encoded by error type** (backend-wide)  
   Exceptions are mostly generic `RuntimeError`/`Exception`; code does not separate retryable vs non-retryable failures.

11. **No per-step retry budgets** (`backend/orchestrator.py`, `backend/worker.py`)  
   Steps do not define max attempts, cooldown, or cumulative deadline, making reliability behavior unpredictable.

12. **No idempotency guard coupled with retries** (pipeline-wide)  
   Safe retries require idempotent side effects, but retry mechanics are missing while side effects (DB updates, notifications) remain vulnerable to duplicate behavior when retries are introduced later.

13. **No observability around retry decisions** (backend-wide)  
   Because retries are mostly absent, there are also no structured logs/metrics for attempt count, backoff delay, and exhaustion reason.
