# Redis Module

This module stores pipeline state using split Redis keys under `job:{job_id}:...`.

## Key Model

- `job:{id}:meta` (HASH): control fields (`hunt_id`, `fcm_token`, `cdn_link`, status, errors, timestamps)
- `job:{id}:steps` (HASH): per-step state (`pending|running|done|failed`)
- `job:{id}:keys` (SET): registry for all keys created for the job
- `job:{id}:utterances`, `job:{id}:utterances_en`, `job:{id}:result` (STRING JSON)
- `job:{id}:items:index` (LIST) + per-item fragments (`items:base:*`, `items:urls:*`, `items:selected:*`, `items:answer:*`)
- `job:{id}:artifact:*` keys for transient audio and pages

## Usage

```python
from rmq_redis import job_repository

job_repository.init_job(
    job_id="my-job-123",
    meta={"hunt_id": 1, "fcm_token": "token", "cdn_link": "https://cdn.example/video.mp4"},
    ttl=86400,
)

job_repository.set_utterances("my-job-123", [{"text": "example"}])
job_repository.set_items_base("my-job-123", [{"question": "Q1", "query": "search query"}])
items = job_repository.get_composed_items("my-job-123")
result = job_repository.get_result("my-job-123")
```

## Ownership

Worker owns only orchestration fields (`meta.status`, `meta.current_step`, error fields, and `steps.*`).
Handlers own pipeline payload keys for their assigned step and should use repository getters/setters only.
