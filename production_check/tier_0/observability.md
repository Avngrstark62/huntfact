# Production Concern: Observability (Tier 0)

Focus: ability to detect, debug, and resolve production issues quickly.

## Release Blockers

1. **No metrics pipeline for reliability/SLO tracking** (backend-wide)  
   There are logs, but no emitted counters/histograms (success rate, step latency, timeout rate, queue lag, failure class), so production health cannot be measured reliably.

2. **No distributed tracing or request/workflow span instrumentation** (backend-wide)  
   Workflow crosses API, RMQ, orchestrator, worker, and many external services without trace context propagation; root-cause analysis across components is very hard.

3. **No end-to-end correlation key consistently logged across all steps** (`backend/router.py`, `backend/orchestrator.py`, `backend/worker.py`, `backend/services/*`)  
   `job_id`/`workflow_id`/`hunt_id` are partially logged but not uniformly included in every step log line.

## High Severity

4. **Exception trace logging is disabled in production API paths** (`backend/router.py`)  
   `exc_info=settings.app.debug` means stack traces are often missing when debug is false, reducing incident diagnosability.

5. **Critical failure telemetry is inconsistent by module** (services/handlers-wide)  
   Some paths log rich context, while others log generic messages or swallow errors (e.g., scrape failures), creating blind spots.

6. **No structured log schema (event name + fields)** (`backend/logging_config.py`, backend-wide usage)  
   Free-form string logs dominate; lack of structured fields makes querying, dashboards, and alerting fragile.

7. **No severity discipline for operationally important events** (backend-wide)  
   Some significant degradation states are logged at `info`/`warning` without clear error classification.

8. **Sensitive/high-volume payload logging pollutes signal** (`backend/orchestrator.py`, some service logs)  
   Large objects (translation/claims/result fragments) are logged, increasing noise and making real incident patterns harder to detect.

## Important Gaps

9. **No explicit queue observability metrics** (`backend/rmq/*`)  
   Missing visibility into consumer lag, in-flight counts, retry counts, and poison-message frequency.

10. **No external dependency health metrics per provider** (OpenAI/AssemblyAI/SearXNG/Firecrawl/Firebase/Chroma paths)  
   No per-provider success/failure/latency counters to identify upstream degradation quickly.

11. **No standardized failure taxonomy in logs** (backend-wide)  
   Errors are emitted as heterogeneous strings (`RuntimeError`, generic “failed”, provider text), making reliable aggregation difficult.

12. **No clear split between user-facing and operator-facing error telemetry** (`backend/router.py`, handlers)  
   Generic API responses are returned, but internal diagnostics are not consistently captured in machine-parseable form.

13. **No alerting hooks visible from code path** (backend-wide)  
   Failures are logged but not wired to an alerting channel/event sink, so critical outages may rely on manual log inspection.
