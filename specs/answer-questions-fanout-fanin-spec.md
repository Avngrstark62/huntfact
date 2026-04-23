# Answer Questions Fanout/Fanin Spec (No New Pipeline Step)

## Objective

Speed up the `ANSWER_QUESTIONS` stage by splitting it into per-question tasks that can run in parallel, while keeping the existing step sequence unchanged:

`SAVE_DATA_TO_RAG -> ANSWER_QUESTIONS -> GENERATE_RESULT`

This spec intentionally avoids introducing any new pipeline step constant.

## Current Behavior (Baseline)

- `SAVE_DATA_TO_RAG` publishes one `ANSWER_QUESTIONS` task.
- `ANSWER_QUESTIONS` loads all items and processes them sequentially in one loop.
- After all items are answered, handler publishes `GENERATE_RESULT`.
- Worker step-level idempotency marks `ANSWER_QUESTIONS` as `done` after one task run.

This creates a bottleneck for jobs with many questions and blocks downstream progress until all answers are generated serially.

## Target Behavior

### High-level flow

1. `SAVE_DATA_TO_RAG` completes ingestion.
2. `SAVE_DATA_TO_RAG` reads all `item_id`s and publishes one `ANSWER_QUESTIONS` task per item (`payload={"item_id": ...}`).
3. Each `ANSWER_QUESTIONS` task answers exactly one question and writes exactly one answer.
4. Each completed per-item task updates Redis progress counters atomically.
5. The last completed item triggers `GENERATE_RESULT` publication exactly once.

### Constraints

- Keep step constants unchanged (`ANSWER_QUESTIONS` remains the step name).
- No additional queue/step constants for dispatch/fanin.
- Preserve existing job state split model and ownership rules.

## Redis Progress Barrier Design

Add QA fanout/fanin tracking keys under `job:{job_id}:qa:*`.

### Keys

- `job:{id}:qa:total` (STRING int)
  - Number of item tasks expected for this job.
- `job:{id}:qa:done` (STRING int)
  - Number of unique item completions counted.
- `job:{id}:qa:failed` (STRING int, optional but recommended)
  - Number of item tasks that ended in failure mode.
- `job:{id}:qa:completed_items` (SET)
  - Item IDs already counted toward `qa:done` (idempotency guard).
- `job:{id}:qa:generate_lock` (STRING)
  - Single-use lock via `SET NX` to ensure only one publish of `GENERATE_RESULT`.

### TTL policy

- Same base TTL as other pipeline keys (24h), refreshed on writes.
- Keep `qa:*` keys until TTL expiry for debugging; do not delete immediately after `GENERATE_RESULT`.

## Fanout Logic in `SAVE_DATA_TO_RAG`

`SAVE_DATA_TO_RAG` handler changes:

1. Run existing page ingestion to RAG.
2. Load ordered item IDs via repository.
3. If item count is zero:
   - log error and fail step (existing behavior pattern).
4. Initialize/reset QA barrier keys:
   - `qa:total = item_count`
   - `qa:done = 0`
   - `qa:failed = 0`
   - delete/clear `qa:completed_items`
   - delete `qa:generate_lock`
5. Publish one `TaskMessage(step=ANSWER_QUESTIONS, payload={"item_id": item_id})` per item.
6. Return `None` from handler (no single next task), because fan-in logic publishes `GENERATE_RESULT`.

## Per-item `ANSWER_QUESTIONS` Logic

`ANSWER_QUESTIONS` handler/service changes from batch mode to single-item mode.

### Input contract

- `job_id` from task envelope
- `item_id` from task payload

### Processing

1. Load base item (`question`, `query`) for `item_id`.
2. If item missing:
   - handle as failed item path (see Failure handling section).
3. Query RAG and call LLM for that one item.
4. Write answer with repository method for that `item_id`.

### Completion barrier update (idempotent)

After processing (success or handled failure):

1. `added = SADD qa:completed_items item_id`
2. If `added == 1`, `done = INCR qa:done`; else this is duplicate delivery and should not increment.
3. Read `total = GET qa:total`.
4. If `done == total`:
   - `SET qa:generate_lock "1" NX EX 86400`
   - if lock acquired, publish `GENERATE_RESULT`
   - if not acquired, do nothing (another worker already published)

## Worker Contract Changes

Current worker behavior is incompatible with fanout because it treats step completion as global for the step name.

### Required worker changes

1. Pass payload into handlers, not only `job_id`.
   - target signature:
     - `async def handle_<step>(job_id: str, payload: dict | None = None) -> Optional[TaskMessage]`
2. Adjust step idempotency for `ANSWER_QUESTIONS`:
   - Do not short-circuit all `ANSWER_QUESTIONS` tasks when step state is `done` before fan-in is complete.
3. Step state transitions for `ANSWER_QUESTIONS`:
   - set `running` when fanout starts
   - keep `running` while per-item tasks are processing
   - set to `done` only once fan-in condition is met (same point where `GENERATE_RESULT` is published)
   - worker remains the source of truth for step state transitions

### Next-task publishing model

- For regular steps: existing model unchanged.
- For `SAVE_DATA_TO_RAG`: publishes multiple tasks internally; worker does not publish one next task.
- For per-item `ANSWER_QUESTIONS`: usually returns no next task; only barrier winner publishes `GENERATE_RESULT`.

## Repository/API Changes

Add repository support for QA barrier operations (preferably atomic or scripted):

- `init_qa_barrier(job_id: str, total: int)`
- `mark_qa_item_completed(job_id: str, item_id: str) -> tuple[bool, int, int]`
  - returns `(counted, done, total)`
- `increment_qa_failed(job_id: str) -> int`
- `try_acquire_generate_lock(job_id: str) -> bool`
- `set_answer_questions_done_if_complete(job_id: str) -> bool` (optional helper for worker/state consistency)

Key helper additions in `rmq_redis/keys.py`:

- `job_qa_total_key(job_id)`
- `job_qa_done_key(job_id)`
- `job_qa_failed_key(job_id)`
- `job_qa_completed_items_key(job_id)`
- `job_qa_generate_lock_key(job_id)`

## Failure Handling Policy

Adopt explicit best-effort completion to avoid stuck jobs:

- If per-item answering fails:
  - write `answer=None` for the item,
  - increment `qa:failed`,
  - still mark the item as completed in barrier accounting.
- No per-item retry policy is introduced in this change.

Rationale:

- Ensures fan-in always progresses and `GENERATE_RESULT` can run.
- Avoids indefinite blocking on a subset of failed items.

## Idempotency Requirements

Because queue delivery is at-least-once, all logic must tolerate duplicates:

- Per-item completion counted once via `SADD completed_items`.
- `qa:done` increments only when `SADD` returns first insert.
- `GENERATE_RESULT` publish guarded by `SET NX` lock.
- Answer writes should be deterministic and safe on duplicate reprocessing.

## Concurrency/Throughput Notes

Fanout enables parallelism but does not automatically increase throughput with a single sequential consumer.

For meaningful speedup, deploy one or both:

- multiple worker replicas/processes consuming the same queue, and/or
- in-process concurrent message handling.

Current `prefetch_count=1` + sequential loop limits per-process parallel execution.

## Observability

Add logs with `job_id` and `item_id` for:

- fanout initialization (`total`)
- per-item start/end/failure
- barrier progress (`done/total`)
- lock acquisition and `GENERATE_RESULT` publication

Optional metrics:

- answer latency per item
- total fanout completion duration
- failed item count per job

## Backward Compatibility

- No API contract changes to clients.
- Existing step constants remain.
- Existing downstream `GENERATE_RESULT` behavior remains, but now triggered by fan-in barrier completion.

## Acceptance Criteria

1. `SAVE_DATA_TO_RAG` publishes one `ANSWER_QUESTIONS` task per `item_id`.
2. Each `ANSWER_QUESTIONS` task processes exactly one item.
3. `qa:done` reaches `qa:total` exactly once per job, even with duplicate message delivery.
4. `GENERATE_RESULT` is published exactly once per job.
5. Worker does not prematurely skip remaining `ANSWER_QUESTIONS` tasks due to global step-state short-circuit.
6. Pipeline completes even when some item answers fail (best-effort policy).
7. End-to-end result generation uses composed items with per-item answers written through existing repository keys.

## Implementation Plan (File-level)

1. `backend/rmq_redis/keys.py`
   - add QA barrier key builders.
2. `backend/rmq_redis/repository.py`
   - add QA barrier helper methods and lock helper.
3. `backend/services/save_data_to_rag/handler.py`
   - replace single next-task return with fanout initialization + multi-publish.
4. `backend/services/answer_questions/handler.py`
   - switch to payload-driven single-item handler.
5. `backend/services/answer_questions/answer_questions.py`
   - add single-item answering function (or refactor existing).
6. `backend/worker.py`
   - pass payload to handlers,
   - adjust idempotency/state handling for `ANSWER_QUESTIONS` fanout lifecycle.
7. `backend/rmq/schemas.py` (optional contract clarification only)
   - ensure payload usage is documented/validated for per-item tasks.

## Finalized Decisions

1. Failed per-item answers are stored as `None`.
2. `ANSWER_QUESTIONS` step state transitions are handled by worker only.
3. `qa:*` keys are retained until TTL expiry for debugging.
4. Per-item retry policy is out of scope for this change.
