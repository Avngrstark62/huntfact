# Production Concern: Observability (Tier 0)

Focus: ability to detect, debug, and resolve production issues quickly.

## Release Blockers

1. **[OPEN] No metrics pipeline for reliability/SLO tracking** (backend-wide)  
   There are logs, but no emitted counters/histograms (success rate, step latency, timeout rate, queue lag, failure class), so production health cannot be measured reliably.

2. **[OPEN] No distributed tracing or request/workflow span instrumentation** (backend-wide)  
   Workflow crosses API, RMQ, orchestrator, worker, and many external services without trace context propagation; root-cause analysis across components is very hard.

3. **[OPEN] No end-to-end correlation key consistently logged across all steps** (`backend/router.py`, `backend/orchestrator.py`, `backend/worker.py`, `backend/services/*`)  
   `job_id`/`workflow_id`/`hunt_id` are partially logged but not uniformly included in every step log line.

4. **[NEW] RMQ correlation identifiers are not propagated into downstream processing logs** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/orchestrator.py`)  
   Queue metadata includes message/correlation identifiers, but they are not consistently carried into worker/orchestrator/service logs for cross-component incident stitching.

## High Severity

5. **[OPEN] Exception trace logging is disabled in production API paths** (`backend/router.py`)  
   `exc_info=settings.app.debug` means stack traces are often missing when debug is false, reducing incident diagnosability.

6. **[OPEN] Critical failure telemetry is inconsistent by module** (services/handlers-wide)  
   Some paths log rich context, while others log generic messages or swallow errors (e.g., scrape failures), creating blind spots.

7. **[OPEN] No structured log schema (event name + fields)** (`backend/logging_config.py`, backend-wide usage)  
   Free-form string logs dominate; lack of structured fields makes querying, dashboards, and alerting fragile.

8. **[OPEN] No severity discipline for operationally important events** (backend-wide)  
   Some significant degradation states are logged at `info`/`warning` without clear error classification.

9. **[OPEN] Sensitive/high-volume payload logging pollutes signal** (`backend/orchestrator.py`, some service logs)  
   Large objects (translation/claims/result fragments) are logged, increasing noise and making real incident patterns harder to detect.

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

15. **[NEW] Validation error observability is reduced to generic message at API boundary** (`backend/app.py`)  
   Global request-validation handler returns a normalized error shape but drops field-level validation context from operator-facing telemetry unless separately captured.
