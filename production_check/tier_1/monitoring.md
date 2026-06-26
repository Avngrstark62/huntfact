# Production Concern: Monitoring (Tier 1)

Focus: ability to detect backend degradation early enough to act before users report failures.

## Major Monitoring Issues

1. **Health monitoring covers only DB and RabbitMQ flags** (`backend/health.py`, `backend/app.py`)  
   Runtime health does not include critical dependencies used in user flow (LLM providers, Firecrawl, SearXNG, Chroma, Firebase), so major outages can pass as healthy.

2. **Dependency health flags are mostly startup-time signals, not continuous checks** (`backend/app.py`, `backend/health.py`)  
   Health state is set during initialization and can become stale after startup failures/reconnections, reducing trust in `/health` as a live monitor.

3. **No backend mechanism for threshold-based incident detection** (backend-wide)  
   There is no code-level path for triggering alerts on spikes in failure rate, latency, or stuck hunts, so problems are likely discovered reactively by users.

4. **No queue backlog/consumer-lag monitoring in processing path** (`backend/rmq/consumer.py`, `backend/worker.py`, `backend/orchestrator.py`)  
   Async pipeline reliability depends on queues, but there are no lag/in-flight/dead-message monitors to detect processing slowdowns early.

## Important Monitoring Gaps

5. **No monitoring for hunt lifecycle SLOs (queued→processing→completed/failed)** (`backend/router.py`, `backend/db/database.py`, `backend/orchestrator.py`)  
   Backend tracks statuses but lacks automated checks for long-lived `processing` hunts or abnormal completion/failure distribution.

6. **Monitoring signal quality is weakened by unstructured logs** (`backend/logging_config.py`)  
   Free-form log messages make it hard to build reliable dashboards/rules for fast anomaly detection.

7. **No synthetic or canary-style end-to-end monitoring path** (backend-wide)  
   There is no automated periodic verification of the full workflow, so silent regressions can persist until real user traffic hits them.
