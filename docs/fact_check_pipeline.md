# 🧠 🎯 CORE DATA MODEL (IMPORTANT)

Everything revolves around this:

```json
{
  "items": [
    {
      "id": "q1",
      "question": "...",
      "query": "...",
      "urls": [],
      "chunks": [],
      "answer": null
    }
  ]
}
```

👉 **1:1 mapping**

* each **question ↔ query ↔ urls ↔ chunks ↔ answer**

---

# 🔥 FULL PIPELINE (STEP-BY-STEP)

---

## 1. `extract_questions_queries`

### Input:

```json
utterances[]
```

### Output:

```json
items[] = [
  {
    "id": "q1",
    "question": "...",
    "query": "..."
  }
]
```

👉 Constraints:

* 1 query per question
* queries are **retrieval-optimized**
* questions are **QA-optimized**

---

## 2. `fetch_urls`

### Input:

```json
items[].query
```

### Process:

* run web search per query

### Output:

```json
items[].urls = [
  { "url": "...", "title": "...", "snippet": "..." }
]
```

👉 Still **per-item mapping preserved**

---

## 3. `select_urls`

### Input:

```json
items[] (question + query + urls)
```

### Process:

* LLM selects top **2–3 URLs per item**

### Output:

```json
items[].urls = [
  { "url": "...", "selected": true }
]
```

👉 No cross-mixing
👉 Selection is **question-aware**

---

## 4. `fetch_pages`

### Input:

```json
all selected URLs (deduplicated globally)
```

### Process:

* scrape once per URL

### Output:

```json
pages = {
  "url1": "clean text...",
  "url2": "clean text..."
}
```

👉 Global cache (important)

---

## 5. `save_data_to_rag`

### Input:

```json
pages
```

### Process:

```text
clean → chunk (200–400 tokens) → embed → store
```

### Output:

```text
RAG index (ephemeral)
```

---

## 6. `answer_questions`

### Input:

```json
items[] + RAG
```

### Process (per item):

```text
query → embed → retrieve top-k chunks
      → [chunks + question] → QA model
```

### Output:

```json
items[].chunks = [...]
items[].answer = "..."
```

---

## 7. `generate_result`

### Input:

```json
utterances + items[] (Q + A)
```

### Process:

* reasoning over:

  * full transcript
  * all Q/A pairs

### Output:

```json
{
  "verdict": "...",
  "confidence": 0.X,
  "explanation": "...",
  "sources": [...]
}
```

---

# 🔁 GLOBAL OPTIMIZATION (IMPORTANT)

Before `fetch_pages`:

```text
collect all selected URLs → deduplicate → scrape once
```

---

# 🧠 FINAL PIPELINE DIAGRAM

```text
                ┌────────────────────────┐
                │     utterances         │
                └─────────┬──────────────┘
                          │
                          ▼
        ┌────────────────────────────────────┐
        │ extract_questions_queries (LLM)    │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ items[]: {question, query}         │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ fetch_urls (search tool)           │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ select_urls (LLM)                  │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ deduplicate URLs                  │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ fetch_pages (scraper)              │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ save_data_to_rag (embedding)       │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ answer_questions (RAG + QA model)  │
        └─────────┬──────────────────────────┘
                  │
                  ▼
        ┌────────────────────────────────────┐
        │ generate_result (LLM reasoning)    │
        └────────────────────────────────────┘
```

---
