# Production Concern: Timeouts (Tier 0)

Focus: every external call and wait path must terminate predictably.

## Release Blockers

1. **Orchestrator RPC chain has no explicit timeout values** (`backend/orchestrator.py`, `backend/rmq/publisher.py`)  
   `publish_task_rpc` supports timeout but all orchestration calls omit it; a stuck task can block a hunt indefinitely.

2. **AssemblyAI HTTP calls have no timeout** (`backend/services/transcriber/assemblyai.py`)  
   Upload, transcript creation, and polling `requests` calls do not set `timeout`, so network stalls can hang workers.

3. **AssemblyAI polling loop is unbounded** (`backend/services/transcriber/assemblyai.py`)  
   Polling continues forever with `sleep(1)` and no max elapsed time / max attempts.

## High Severity

4. **OpenAI chat/structured-output calls have no per-call timeout budget** (`backend/llm.py`, all `services/*` using `llm.call_with_schema`)  
   LLM calls can hang on provider/network slowness and block workflow progress.

5. **Embedding calls have no timeout** (`backend/services/rag_storage/rag_storage.py`, `backend/services/embeddings/embeddings.py`)  
   Embedding generation is synchronous with no bounded wait, risking long stalls under provider issues.

6. **Firecrawl scrape calls have no timeout control** (`backend/services/firecrawl/firecrawl.py`)  
   `app.scrape(...)` has no explicit timeout at call boundary, so scraper latency spikes can block pipeline steps.

7. **Firebase notification send has no timeout guard** (`backend/services/notification_sender/notification_sender.py`)  
   `messaging.send(...)` call has no explicit timeout behavior enforced by app code.

8. **RabbitMQ workflow/task consumption has no message-processing deadline** (`backend/rmq/consumer.py`)  
   `raw_message.process()` context has no app-level processing timeout, so long-running handlers can monopolize consumers.

## Important Gaps

9. **No global end-to-end timeout (SLO budget) per hunt** (pipeline-wide)  
   Step-level waits exist in parts (e.g., FFmpeg), but there is no total workflow deadline after which hunt is failed deterministically.

10. **Timeout behavior is inconsistent across integrations** (pipeline-wide)  
   SearXNG and JWKS have explicit timeouts, but transcription/LLM/Firecrawl/notifications do not, creating uneven reliability.

11. **Timeout expirations are not classified into a distinct failure type** (`backend/orchestrator.py`, handlers)  
   Timeout-induced failures are merged into generic errors, making operational diagnosis and auto-retry policy harder.

12. **No timeout-driven recovery for hunts already in `processing`** (`backend/router.py`, `backend/db/database.py`)  
   When a timeout-like stall occurs, hunts can remain in `processing` without automatic transition to `failed` after deadline.
