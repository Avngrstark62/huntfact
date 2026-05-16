# Fact-Checking Pipeline: `TRANSCRIBE` -> `SAVE_RESULT_TO_DB`

This document explains the exact runtime flow from the `TRANSCRIBE` step to the final DB write.

## Scope and Entry Point

- The workflow orchestrator sends `TRANSCRIBE` after `EXTRACT_AUDIO`.
- `TRANSCRIBE` input payload (from orchestrator):
  - `audio_bytes_b64` (base64 audio bytes)
  - `audio_format` (`"aac"` or `"mp3"`)

From here, steps run in this order:
1. `TRANSCRIBE`
2. `TRANSLATE`
3. `EXTRACT_CLAIM_CLUSTERS`
4. Per-cluster loop: `URL_FETCHER` -> `WEB_SCRAPER` -> `CLAIM_VERIFIER`
5. Cluster table merge
6. `SAVE_RESULT_TO_DB`

## 1) `TRANSCRIBE`

### Input payload
```json
{
  "audio_bytes_b64": "...",
  "audio_format": "aac|mp3"
}
```

### What happens
- `services/transcriber/handler.py` validates both fields exist.
- It base64-decodes `audio_bytes_b64` into raw bytes.
- It calls `services/transcriber/assemblyai.py::transcribe_audio(audio_bytes, fmt)`.
- `transcribe_audio` does:
  - Upload bytes to AssemblyAI `/upload`
  - Submit transcript job to `/transcript` with `speech_models: ["universal-2"]`
  - Poll transcript status until `completed` or `error`
- On success, transcript text is returned.

### Output payload
```json
{
  "transcript_text": "<full transcript>",
  "error": null
}
```

## 2) `TRANSLATE`

### Input payload
```json
{
  "transcript_text": "<full transcript>"
}
```

### What happens
- `services/translator/handler.py` validates `transcript_text`.
- Calls `services/translator/translator.py::translate_text`.
- `translate_text` sends a strict translation prompt to `llm.call_with_schema` using:
  - model: `settings.cheap_model`
  - schema: `TranslationResponse { translated_text: str }`
- The prompt enforces: preserve meaning/tone, fix only obvious ASR errors, no summarization.

### Output payload
```json
{
  "translated_text": "<english text>",
  "error": null
}
```

## 3) `EXTRACT_CLAIM_CLUSTERS`

### Input payload
```json
{
  "content": "<translated_text>"
}
```

### What happens
- `services/claim_extractor/handler.py` validates `content`.
- Calls `extract_claim_clusters(content)`.
- `claim_extractor.py` asks LLM (`settings.reasoning_model`) for:
  - objective factual claims only
  - grouped into clusters where each cluster can be verified with one search intent
- Output is schema-validated as `ClaimClustersResponse`.
- `_normalize_clusters` removes empty/duplicate claims per cluster.

### Output payload
```json
{
  "clusters": [
    ["claim 1", "claim 2"],
    ["claim 3"]
  ],
  "error": null
}
```

## 4) Per-cluster verification loop

The orchestrator filters to valid non-empty clusters, then runs one loop per cluster via `asyncio.gather` (parallel fan-out).

For each cluster:

### 4.1 `URL_FETCHER`
- Input:
  ```json
  { "claims": ["..."] }
  ```
- Logic:
  - Generate 1-3 search queries using LLM (`settings.reasoning_model`)
  - Normalize/dedupe queries (hard cap at 5)
  - Query SearxNG for each query
  - Extract unique `{title, url}` entries
- Output:
  ```json
  {
    "results": [
      { "query": "...", "urls": [{ "title": "...", "url": "..." }] }
    ],
    "error": null
  }
  ```

### 4.2 `WEB_SCRAPER`
- Input:
  ```json
  {
    "claims": ["..."],
    "url_fetcher_results": { "results": [...] }
  }
  ```
- Logic:
  - Flatten URL candidates from all query results
  - Use LLM to select best candidate indices (max 5 URLs)
  - Fetch markdown for selected URLs using Firecrawl
  - Build context:
    ```json
    { "sources": [{ "source_id": 1, "url": "...", "title": "...", "query": "...", "content": "..." }] }
    ```
- Output:
  ```json
  {
    "context": { "sources": [...] },
    "error": null
  }
  ```

### 4.3 `CLAIM_VERIFIER`
- Input:
  ```json
  {
    "claims": ["..."],
    "context": { "sources": [...] }
  }
  ```
- Logic:
  - Normalize claims and usable context sources
  - If no sources: return one `no verdict` row per claim
  - Else run LLM (`settings.reasoning_model`) with strict rules:
    - use only provided sources
    - verdict in `{true, false, partially true, no verdict}`
    - include only source URLs actually used
  - Normalize final rows so every input claim has one row
- Output:
  ```json
  {
    "table": {
      "rows": [
        {
          "claim": "...",
          "verdict": "true|false|partially true|no verdict",
          "sources": ["https://..."],
          "explanation": "..."
        }
      ]
    },
    "error": null
  }
  ```

## 5) Cluster fan-in (merge)

- Orchestrator merges all per-cluster tables into one table:
  ```json
  { "rows": [ ...all rows from all cluster tables... ] }
  ```
- Merge is append-based; it concatenates `rows` from each cluster table in completion order.

## 6) `SAVE_RESULT_TO_DB`

### Input payload
```json
{
  "hunt_id": 123,
  "table": { "rows": [...] }
}
```

### What happens
- `services/save_result_to_db/handler.py` validates:
  - `hunt_id` is `int`
  - `table` is `dict`
- Calls `save_result_to_db(hunt_id, table)`:
  - serializes table with `json.dumps(..., ensure_ascii=False)`
  - calls `db.update_hunt_result(session, hunt_id, serialized_result)`
- `db.update_hunt_result` writes:
  - `hunt.result = serialized_result`
  - `hunt.status = "completed"`
  - `hunt.error_message = None`
  - `hunt.completed_at = now(UTC)`

### Output payload
```json
{
  "saved": {
    "hunt_id": 123,
    "result": "{\"rows\": [...]}"
  },
  "error": null
}
```

## Failure Behavior in This Scope

- Any step returning RPC status `error` causes orchestrator failure.
- On failure, orchestrator updates hunt status to `failed` with the exception message.
