# Production Concern: Background Jobs (Tier 1)

Focus: ensuring async workflow tasks are not lost, stuck, or silently abandoned.

## Major Background Job Issues

1. **[FIXED] Workflow can be marked `processing` before publish succeeds** (`backend/router.py`, `backend/orchestrator.py`)  
   Hunt state now remains queued until workflow execution actually starts; `processing` is set by orchestrator on active execution, avoiding false in-flight status after publish failure.

2. **[FIXED] No built-in recovery for stuck `processing` hunts** (`backend/workflow_cleanup.py`, `backend/db/database.py`, `backend/config.py`)  
   Cleanup process now periodically marks stale `processing` and stale `queued` hunts as failed and removes stale admissions.

## Important Background Job Gaps

3. **[OPEN] RPC step orchestration has no explicit timeout budget in calls** (`backend/orchestrator.py`, `backend/rmq/publisher.py`)  
   `publish_task_rpc` supports timeout but orchestrator calls it without one, allowing individual step waits to block indefinitely under dependency hangs.

4. **[OPEN] API health does not verify worker/orchestrator liveness** (`backend/health.py`, `backend/app.py`)  
   Service can report healthy while background processors are down, so jobs may queue indefinitely without active execution.

5. **[OPEN] Background execution state is minimally persisted** (`backend/db/database.py`, `backend/orchestrator.py`)  
   Only coarse hunt status/error are stored; absence of per-step attempt/history metadata makes safe resume and forensic recovery difficult after crashes.
