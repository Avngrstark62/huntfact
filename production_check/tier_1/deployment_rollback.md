# Production Concern: Deployment & Rollback (Tier 1)

Focus: ability to release backend changes safely and recover quickly from bad deployments.

## Major Deployment & Rollback Issues

1. **Single-process container startup does not include orchestrator/worker lifecycle** (`backend/Dockerfile`, `backend/main.py`, `backend/setup_commands.md`)  
   Container `CMD` runs only API (`python main.py`), while orchestrator and worker are separate manual processes; incomplete rollout can leave background pipeline non-functional after deploy.

2. **No built-in deployment guard to verify all critical services before serving traffic** (`backend/app.py`, `backend/health.py`)  
   Startup logs failures for dependencies but app still boots; releases can appear up while key processing dependencies are unavailable.

3. **Migration execution is not integrated into a robust rollout workflow** (`backend/docker/migrate.sh`, `backend/Dockerfile`, `backend/setup_commands.md`)  
   Migrations exist but are external/manual in current flow; partial or skipped migration during deploy can break runtime behavior under new code.

4. **No explicit rollback orchestration for app + schema + async workers** (backend-wide)  
   Alembic supports downgrades, but there is no codified rollback runbook/mechanism ensuring coordinated rollback across API, orchestrator, worker, and DB state.

## Important Deployment & Rollback Gaps

5. **No staged release strategy (canary/blue-green) visible in backend release assets** (backend-wide)  
   Without progressive rollout controls, bad releases are more likely to impact all traffic before detection.

6. **No release-time compatibility checks between old/new versions and queued messages** (`backend/rmq/schemas.py`, `backend/orchestrator.py`, `backend/worker.py`)  
   Message payloads are loosely typed dicts, and there is no explicit compatibility gate for in-flight queue data during version transitions.

7. **No automated post-deploy smoke verification path in repository workflow** (`backend/setup_commands.md`)  
   Current startup guidance is manual process commands; absence of scripted smoke checks increases time-to-detect after faulty deployments.
