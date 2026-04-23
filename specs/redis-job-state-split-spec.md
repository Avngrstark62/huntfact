# Redis Job State Split Spec

## Objective

Replace the current single-key JSON job state (`job:{job_id}`) with a split Redis key model so each pipeline step reads/writes only the state it owns. The primary goal is to eliminate full-document rewrites and reduce write amplification, payload size per operation, and conflict surface.

This spec is based on the current backend pipeline in:
- `backend/router.py`
- `backend/worker.py`
- `backend/rmq_redis/*`
- `backend/services/*/handler.py`
- `backend/test_scripts/test_handler.py`

## Current Behavior (Baseline)

- Job state is initialized in `router.start_hunt()` via `set_job_data(job_id, job_state, ttl=86400)`.
- Worker fetches full state (`get_job_data`) before step execution.
- Each step mutates the in-memory dict.
- Worker writes back full state (`update_job_data`) after every step.
- `handle_fetch_pages()` also performs an extra direct `update_job_data`, causing duplicate full writes for that step.

Current mutable fields in one JSON blob include:
- control/meta: `hunt_id`, `fcm_token`, `cdn_link`
- artifacts: `audio_bytes`, `pages_data`
- pipeline: `utterances`, `utterances_english`, `items`, `result`
- telemetry/error: transcription/audio error fields

## Target Redis Data Model

All keys are scoped under `job:{job_id}:...`.

### 1) Meta and control plane

- `job:{id}:meta` (HASH)
  - `hunt_id`
  - `fcm_token`
  - `cdn_link`
  - `status` (`queued|running|failed|completed`)
  - `current_step`
  - `created_at`
  - `updated_at`
  - `error_code` (optional)
  - `error_message` (optional)

- `job:{id}:steps` (HASH)
  - one field per step with values like `pending|running|done|failed`
  - field names map to RMQ constants, e.g. `EXTRACT_AUDIO`, `TRANSCRIBE`, ...

- `job:{id}:keys` (SET)
  - registry of all keys created for this job; used for cleanup and inspection.

### 2) Pipeline outputs

- `job:{id}:utterances` (STRING JSON)
  - output from `TRANSCRIBE`, written once.

- `job:{id}:utterances_en` (STRING JSON)
  - output from `TRANSLATE`, written once.

- `job:{id}:items:index` (Redis LIST)
  - stable ordered item IDs (recommended: deterministic IDs or `item_0..item_n`).

Per item split (write-once by owner step):
- `job:{id}:items:base:{item_id}` (STRING JSON)
  - `{ "question": "...", "query": "..." }`
  - written by `EXTRACT_QUESTIONS_QUERIES`.
- `job:{id}:items:urls:{item_id}` (STRING JSON)
  - `{ "urls": [ ... ] }`
  - written by `FETCH_URLS`.
- `job:{id}:items:selected:{item_id}` (STRING JSON)
  - `{ "selected_urls": [ ... ] }`
  - written by `SELECT_URLS`.
- `job:{id}:items:answer:{item_id}` (STRING JSON)
  - `{ "answer": "..." }`
  - written by `ANSWER_QUESTIONS`.

### 3) Heavy artifacts

- `job:{id}:artifact:audio` (STRING)
  - base64 audio payload or encoded binary strategy (see constraints below).
- `job:{id}:artifact:audio_meta` (HASH)
  - `format`, `error`.

- `job:{id}:artifact:pages:index` (SET)
  - page IDs: `p0`, `p1`, ...

- `job:{id}:artifact:pages:{page_id}` (STRING JSON)
  - `{ "url": "...", "scraped_content": "..." }`

### 4) Result

- `job:{id}:result` (STRING JSON)
  - final result object written by `GENERATE_RESULT`.

## Step Ownership Matrix

This matrix defines which component is allowed to write which keys.

0. `worker` (`worker.py`) orchestration-only ownership
   - writes: `meta.status`, `meta.current_step`, `meta.updated_at`, `meta.error_code`, `meta.error_message`, `steps.{step}`.
   - does not write pipeline payload keys (`utterances`, `items:*`, `artifact:*`, `result`).

1. `start_hunt` (`router.py`)
   - writes: `meta`, `steps` init, `keys`.
   - special path (existing hunt with result): also writes `result`.

2. `EXTRACT_AUDIO`
   - reads: `meta.cdn_link`
   - writes: `artifact:audio`, `artifact:audio_meta`.

3. `TRANSCRIBE`
   - reads: `artifact:audio`, `artifact:audio_meta.format`
   - writes: `utterances`, optional transcript stats in `meta` or dedicated hash.

4. `TRANSLATE`
   - reads: `utterances`
   - writes: `utterances_en`.

5. `EXTRACT_QUESTIONS_QUERIES`
   - reads: `utterances_en`
   - writes: `items:index`, `items:base:*`.

6. `FETCH_URLS`
   - reads: `items:index`, `items:base:*`
   - writes: `items:urls:*`.

7. `SELECT_URLS`
   - reads: `items:index`, `items:base:*`, `items:urls:*`
   - writes: `items:selected:*`.

8. `FETCH_PAGES`
   - reads: `items:index`, `items:selected:*`
   - writes: `artifact:pages:index`, `artifact:pages:*`.

9. `SAVE_DATA_TO_RAG`
   - reads: `artifact:pages:index`, `artifact:pages:*`
   - writes: no pipeline payload keys.
   - cleanup: delete `artifact:pages:*` and `artifact:pages:index` after successful ingest.

10. `ANSWER_QUESTIONS`
    - reads: `items:index`, `items:base:*` (query)
    - writes: `items:answer:*`.

11. `GENERATE_RESULT`
    - reads: `items:index`, all item fragments, `utterances_en`
    - writes: `result`.

12. `SAVE_RESULT_TO_DB`
    - reads: `meta.hunt_id`, `result`
   - writes: no pipeline payload keys.

13. `NOTIFY`
    - reads: `meta.fcm_token`, `result`
   - writes: no pipeline payload keys.

## Redis Access Layer Changes

Replace generalized blob helpers with a repository-style API in `backend/rmq_redis/`.

### New module layout

- `backend/rmq_redis/keys.py`
  - key builders for all key types.
- `backend/rmq_redis/repository.py`
  - high-level read/write methods used by router/worker/handlers.
- `backend/rmq_redis/codec.py` (optional)
  - JSON serialization/deserialization with defensive error handling.

### Required repository methods (minimum)

- Job lifecycle
  - `init_job(job_id, meta: dict, ttl: int)`
  - `set_step_state(job_id, step: str, state: str)`
  - `get_step_state(job_id, step: str) -> Optional[str]`
  - `set_job_status(job_id, status: str, current_step: Optional[str] = None, error_code: Optional[str] = None, error_message: Optional[str] = None)`
  - `set_meta_fields(job_id, fields: dict)`
  - `get_meta_fields(job_id, fields: list[str]) -> dict`
  - `job_exists(job_id) -> bool`
  - `delete_job(job_id)`
  - `register_job_key(job_id, redis_key: str)`
  - `iter_job_keys(job_id)`

- Utterance/result state
  - `set_utterances(job_id, utterances)`
  - `get_utterances(job_id)`
  - `set_utterances_en(job_id, utterances_en)`
  - `get_utterances_en(job_id)`
  - `set_result(job_id, result)`
  - `get_result(job_id)`

- Item fragments
  - `set_items_base(job_id, items)` (creates index + base keys)
  - `get_item_base(job_id, item_id)`
  - `set_item_urls(job_id, item_id, urls)`
  - `get_item_urls(job_id, item_id)`
  - `set_item_selected_urls(job_id, item_id, selected_urls)`
  - `get_item_selected_urls(job_id, item_id)`
  - `set_item_answer(job_id, item_id, answer)`
  - `get_item_answer(job_id, item_id)`
  - `iter_item_ids(job_id)`
  - `get_composed_items(job_id)` (merge fragments for consumers)

- Artifacts
  - `set_audio(job_id, audio_b64, fmt, error=None)`
  - `get_audio(job_id) -> (audio_b64, fmt, error)`
  - `delete_audio(job_id)`
  - `set_pages(job_id, pages_data)` (creates page index and page keys)
  - `iter_pages(job_id)`
  - `delete_pages(job_id)`

## Worker and Handler Contract Changes

Current handler signature is:
`async def handle_<step>(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]`

Target contract (required):
- Handlers must not accept `job_state`.
- Handlers must not return a state dict.
- Handler signature becomes:
  - `async def handle_<step>(job_id: str) -> Optional[TaskMessage]`
- Handlers read required inputs from repository getters and write only owned outputs via repository setters.
- Worker must no longer call `update_job_data` (or any full-state writeback) after handler return.
- Worker responsibilities are limited to orchestration:
  - set step/meta status (`running|done|failed`)
  - perform idempotency fast-path check (`steps.{step} == done`) before invoking handler
  - call step handler
  - publish next task if returned

## TTL and Cleanup Policy

Defaults:
- base TTL: 24h for meta, steps, utterances, items, result.
- short TTL (1-2h) for heavy artifacts (`artifact:audio`, `artifact:pages:*`), plus explicit deletes.

Required behavior:
- on every write, preserve or refresh TTL consistently via shared helper.
- if job completes successfully:
  - keep `meta`, `steps`, `result` until base TTL.
  - remove transient artifacts immediately.
- if job fails:
  - keep state until TTL for debugging.

## Idempotency and Conflict Controls

Because RMQ consumer is at-least-once, repeated step execution is possible.

Required guards:
- Worker-level step state check before handler invocation (authoritative):
  - if `steps.{step} == done`, skip step body (idempotent fast-path).
- Handler-level defensive check is optional for safety, but worker check is the source of truth.
- Use write-once semantics for owned fragment keys where possible:
  - `SETNX` or existence checks for `items:base:*`, `items:urls:*`, etc.
- Never perform cross-step overwrites (e.g., URL step must not rewrite answer keys).

## Backward Compatibility / Migration Plan

### Phase A: Introduce new model with dual writes
- Add repository and key builders.
- Switch all handlers to the new contract:
  - `async def handle_<step>(job_id: str) -> Optional[TaskMessage]`
  - no `job_state` argument and no dict return.
- Worker invokes handlers with `job_id` only and manages step/meta status transitions.
- Router initializes split keys via repository; optional rollback dual-write of monolith key may remain temporarily.
- Worker/handlers do not rely on monolith `job:{id}` for control flow.

### Phase B: Read from split keys
- Complete step-by-step migration of handler internals to repository split getters/setters.
- Remove handler-local direct calls to monolith helpers (notably in `fetch_pages` handler).
- Remove any remaining worker usage of monolith helpers (`get_job_data` / `update_job_data`).

### Phase C: Remove monolith
- Delete `get_job_data/set_job_data/update_job_data` usage from worker/router/handlers.
- Keep compatibility shim only if needed for old test scripts.

## File-Level Implementation Plan

### Create / update Redis layer
- Add:
  - `backend/rmq_redis/keys.py`
  - `backend/rmq_redis/repository.py`
  - optional `backend/rmq_redis/codec.py`
- Update:
  - `backend/rmq_redis/__init__.py` exports
  - retain legacy helpers temporarily for transition.

### Router
- `backend/router.py`
  - replace `set_job_data(...)` initialization with repository `init_job(...)`.
  - for existing-hunt-with-result path: write `result` key directly.

### Worker
- `backend/worker.py`
  - replace `get_job_data(...)` with minimal data readiness checks and repository-backed reads inside handlers.
  - remove monolith `update_job_data(...)` call.
  - update step status transitions in `meta`/`steps`.

### Handlers (all pipeline steps)
- `backend/services/*/handler.py`
  - change signatures to `handle_<step>(job_id: str) -> Optional[TaskMessage]`.
  - read required inputs through repository getters only.
  - write outputs through repository setters for owned keys only.
  - remove intra-handler `update_job_data` usage (`fetch_pages`).

### Test scripts
- `backend/test_scripts/test_handler.py`
  - adapt to split state loading (compose required step inputs through repository), or mark as legacy and add new script for split state.

### Docs
- update `backend/rmq_redis/README.md` to reflect split-key usage and ownership model.

## Non-Goals

- No change to business logic of extraction/transcription/search/selection/answering.
- No queue topology change.
- No schema change in Postgres.
- No change to external API payload contracts.

## Risks and Mitigations

- Risk: partial migration causes mixed reads/writes.
  - Mitigation: dual-write + feature flag or phased branch merge.

- Risk: per-item key fan-out increases command count.
  - Mitigation: use pipelining for batch writes/reads.

- Risk: item ordering instability.
  - Mitigation: explicit `items:index` with stable IDs.

- Risk: legacy scripts/tools expect monolith.
  - Mitigation: temporary compatibility adapter.

## Acceptance Criteria

1. No step performs full-state read-modify-write of `job:{id}` JSON.
2. `worker.py` no longer calls monolith `update_job_data`.
3. `worker.py` no longer calls monolith `get_job_data` for pipeline state.
4. All handlers use `handle_<step>(job_id: str) -> Optional[TaskMessage]` (no `job_state` arg, no dict return).
5. `fetch_pages` path no longer triggers duplicate Redis writes.
6. Item data is split into per-step fragments and composed on read.
7. End-to-end pipeline succeeds for:
   - fresh job
   - existing hunt with result (notify-only path)
8. Transient artifacts (`audio`, `pages`) are cleaned after downstream consumption.
9. Redis keyspace for a running job matches the model defined in this spec.

## Open Decisions (to finalize before coding)

1. Item ID format:
   - deterministic hash (`question|query`) vs sequential IDs.
2. Storage encoding for audio:
   - keep base64 (simpler) vs binary mode key (requires redis client decode strategy changes).
3. TTL refresh policy:
   - preserve initial TTL vs refresh on each successful step.
