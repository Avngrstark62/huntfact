# Production Concern: Deployment & Rollback (Tier 1)

Focus: ability to release backend changes safely and recover quickly from bad deployments.

## Major Deployment & Rollback Issues

1. **[OPEN] API, orchestrator, and worker startup is not coordinated** (`backend/main.py`, `backend/setup_commands.md`)  
   Runtime still relies on separate manual process startup for API, orchestrator, and worker; partial rollout can leave background processing non-functional after deploy.

2. **[OPEN] No built-in deployment guard verifies all critical services before serving traffic** (`backend/app.py`, `backend/health.py`)  
   Startup logs dependency initialization failures but app still boots; release can appear up while key processing dependencies are unavailable.

3. **[OPEN] Migration execution is not integrated into a robust rollout workflow** (`backend/setup_commands.md`, `backend/alembic/env.py`)  
   Migrations exist but are still external/manual in current flow; skipped or partial migration during deploy can break runtime behavior under new code.

4. **[OPEN] No explicit rollback orchestration for app + schema + async workers** (backend-wide)  
   Alembic supports downgrades, but there is no codified rollback runbook/mechanism ensuring coordinated rollback across API, orchestrator, worker, and DB state.

## Important Deployment & Rollback Gaps

5. **[OPEN] No staged release strategy (canary/blue-green) is visible in backend release assets** (backend-wide)  
   Without progressive rollout controls, bad releases are more likely to impact all traffic before detection.

6. **[OPEN] No release-time compatibility checks exist between old/new versions and queued messages** (`backend/rmq/schemas.py`, `backend/orchestrator.py`, `backend/worker.py`)  
   Message payloads are loosely typed dicts, and there is no explicit compatibility gate for in-flight queue data during version transitions.

7. **[OPEN] No automated post-deploy smoke verification path exists in repository workflow** (`backend/setup_commands.md`)  
   Current startup guidance is manual process commands; absence of scripted smoke checks increases time-to-detect after faulty deployments.
