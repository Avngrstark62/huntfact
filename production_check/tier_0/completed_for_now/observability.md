# Production Concern: Observability (Tier 0)

Focus: ability to detect, debug, and resolve production issues quickly.

## Release Blockers

1. **[OPEN] No metrics pipeline for reliability/SLO tracking** (backend-wide)  
   There are logs, but no emitted counters/histograms (success rate, step latency, timeout rate, queue lag, failure class), so production health cannot be measured reliably.

2. **[OPEN] No distributed tracing or request/workflow span instrumentation** (backend-wide)  
   Workflow crosses API, RMQ, orchestrator, worker, and many external services without trace context propagation; root-cause analysis across components is very hard.

3. **[PARTIALLY FIXED] End-to-end correlation key is improved but not fully consistent across all steps** (`backend/router.py`, `backend/orchestrator.py`, `backend/worker.py`, `backend/services/*`)  
   `request_id`/`workflow_id`/`hunt_id`/`task_id` are now propagated in many active paths, but not uniformly present in all lower-level provider/service logs.

4. **[PARTIALLY FIXED] RMQ correlation identifiers are propagated in queue/worker paths but not end-to-end downstream** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/orchestrator.py`)  
   Queue metadata and RPC correlation IDs are now logged in consumer/worker/publisher paths, but these identifiers are not consistently carried into all downstream service logs.

## High Severity

5. **[OPEN] Exception trace logging is disabled in production API paths** (`backend/router.py`)  
   `exc_info=settings.app.debug` means stack traces are often missing when debug is false, reducing incident diagnosability.

6. **[OPEN] Critical failure telemetry is inconsistent by module** (services/handlers-wide)  
   Some paths log rich context, while others log generic messages or swallow errors (e.g., scrape failures), creating blind spots.

7. **[FIXED] Structured log schema is now in place for active backend paths** (`backend/logging_config.py`, backend-wide usage)  
   `log_event(...)` plus `JsonFormatter` now emit structured fields (`event`, `status`, `component`, `service`, contextual identifiers), which materially improves queryability and machine parsing.

8. **[OPEN] No severity discipline for operationally important events** (backend-wide)  
   Some significant degradation states are logged at `info`/`warning` without clear error classification.

9. **[PARTIALLY FIXED] High-volume payload logging is reduced but not comprehensively governed** (`backend/orchestrator.py`, some service logs)  
   Many paths now log compact summaries (`result_summary`) instead of raw payloads, but there is still no strict backend-wide policy preventing noisy/sensitive payload logging in all modules.

## Important Gaps

10. **[OPEN] No explicit queue observability metrics** (`backend/rmq/*`)  
   Missing visibility into consumer lag, in-flight counts, retry counts, and poison-message frequency.

11. **[OPEN] No external dependency health metrics per provider** (OpenAI/AssemblyAI/SearXNG/Firecrawl/Firebase/Chroma paths)  
   No per-provider success/failure/latency counters to identify upstream degradation quickly.

12. **[OPEN] No standardized failure taxonomy in logs** (backend-wide)  
   Errors are emitted as heterogeneous strings (`RuntimeError`, generic “failed”, provider text), making reliable aggregation difficult.

13. **[OPEN] No clear split between user-facing and operator-facing error telemetry** (`backend/router.py`, handlers)  
   Generic API responses are returned, but internal diagnostics are not consistently captured in machine-parseable form.

14. **[OPEN] No alerting hooks visible from code path** (backend-wide)  
   Failures are logged but not wired to an alerting channel/event sink, so critical outages may rely on manual log inspection.

15. **[OPEN] Validation error observability is reduced to generic message at API boundary** (`backend/app.py`)  
   Global request-validation handler returns a normalized error shape but drops field-level validation context from operator-facing telemetry unless separately captured.

## New Issues

16. **[NEW] Notification-step failure lacks explicit error telemetry in orchestrator completion path** (`backend/orchestrator.py`)  
   `NOTIFY` exceptions are caught and converted into `notify_status="failed"` without logging `error_type`/`error_message`, making push-delivery incidents hard to debug.

17. **[NEW] JSON file logging setup can fail process startup when log path is not writable** (`backend/logging_config.py`)  
   File-handler initialization always creates a directory/file without guarded fallback; permission/path failures can break startup before application logic runs.
