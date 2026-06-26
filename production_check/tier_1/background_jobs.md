# Production Concern: Background Jobs (Tier 1)

Focus: ensuring async workflow tasks are not lost, stuck, or silently abandoned.

## Major Background Job Issues

1. **No effective retry mechanism in task contract execution** (`backend/rmq/schemas.py`, `backend/worker.py`, `backend/orchestrator.py`)  
   `TaskMessage.retry_count` exists but is not actively used to requeue/retry failed steps, so transient failures can end workflow progress instead of recovering.

2. **No dead-letter path for failed queue messages** (`backend/rmq/consumer.py`, `backend/app.py`)  
   Queue declarations and consumers do not configure explicit DLQ handling, so failed jobs are harder to inspect, replay, and recover safely.

3. **Workflow can be marked `processing` before publish succeeds** (`backend/router.py`, `backend/rmq/publisher.py`)  
   In queued-hunt flow, status transitions to `processing` before `publish_workflow`; if publish fails, hunt can remain in processing without an active job.

4. **No built-in recovery for stuck `processing` hunts** (`backend/router.py`, `backend/db/database.py`, `backend/orchestrator.py`)  
   There is no sweeper/reaper to requeue or fail old in-flight jobs, so interrupted workers/orchestrators can leave hunts permanently stranded.

## Important Background Job Gaps

5. **RPC step orchestration has no explicit timeout budget in calls** (`backend/orchestrator.py`, `backend/rmq/publisher.py`)  
   `publish_task_rpc` supports timeout but orchestrator calls it without one, allowing individual step waits to block indefinitely under dependency hangs.

6. **API health does not verify worker/orchestrator liveness** (`backend/health.py`, `backend/app.py`)  
   Service can report healthy while background processors are down, so jobs may queue indefinitely without active execution.

7. **Background execution state is minimally persisted** (`backend/db/database.py`, `backend/orchestrator.py`)  
   Only coarse hunt status/error are stored; absence of per-step attempt/history metadata makes safe resume and forensic recovery difficult after crashes.
