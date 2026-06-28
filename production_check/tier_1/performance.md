# Production Concern: Performance (Tier 1)

Focus: user-perceived latency and throughput bottlenecks in normal usage.

## Major Performance Issues

1. **Most workflow stages run as sequential RPC hops** (`backend/orchestrator.py`)  
   Outside a few parallel branches, many expensive steps are awaited one-by-one, increasing end-to-end latency.

2. **Blocking network calls inside async execution paths** (`backend/llm.py`, `backend/services/transcriber/assemblyai.py`, `backend/services/url_fetcher/url_fetcher.py`, `backend/services/firecrawl/firecrawl.py`)  
   Sync HTTP/client calls run in async flow and can block event-loop progress under load.

3. **RabbitMQ consumer concurrency is heavily limited** (`backend/config.py`, `backend/rmq/connection.py`)  
   `prefetch_count=1` significantly caps throughput for worker/orchestrator message processing.

4. **Per-query fixed sleep adds avoidable latency** (`backend/services/url_fetcher/url_fetcher.py`)  
   A hard `2s` delay between search queries increases response time linearly with query count.

5. **AssemblyAI polling loop adds latency overhead** (`backend/services/transcriber/assemblyai.py`)  
   Fixed `1s` polling cadence creates cumulative wait even when provider is near-ready.

## Important Performance Gaps

6. **No caching for repeated expensive operations** (pipeline-wide)  
   Repeated requests for same/near-same claims and retrieval paths re-run search, scrape, embedding, and verification work.

7. **No adaptive fast-path for already sufficient evidence** (`backend/services/claim_verifier/claim_verifier.py`, `backend/services/web_scraper/web_scraper.py`)  
   Pipeline does not short-circuit costly retrieval/verification when high-quality evidence is already present.

8. **Potentially large LLM context assembly in verifier step** (`backend/services/claim_verifier/claim_verifier.py`)  
   Concatenated retrieved chunks can become long prompt bodies and inflate latency.

9. **RAG ingestion can become heavy on large pages** (`backend/services/rag_storage/rag_storage.py`)  
   Chunking + embedding generation can create large per-request compute spikes without dynamic throttling.

10. **No explicit latency targets or perf instrumentation at step level** (backend-wide)  
   Logs show start/completion, but no systematic p50/p95 stage timing telemetry to control regressions.
