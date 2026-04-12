# Page Scraping Pipeline – Technical Specification (MVP)

## 1. Objective

Build a **resilient page scraping pipeline** that:

* Takes a list of URLs (from search layer)
* Fetches pages in parallel
* Extracts main content
* Returns structured, LLM-ready output

### Constraints

* Max latency: ~5–8 seconds total
* Parallel processing (5–10 URLs)
* Partial success allowed
* No browser usage unless necessary

---

## 2. High-Level Architecture

```
URL List
   ↓
Async Fetcher (aiohttp)
   ↓
Validator
   ↓
Extractor (trafilatura)
   ↓
Fallbacks (retry / BeautifulSoup / Playwright)
   ↓
Aggregator
   ↓
Final Response
```

---

## 3. Modules & Responsibilities

### 3.1 fetcher.py

**Responsibilities:**

* Perform async HTTP GET requests
* Apply timeout, retries, headers

**Requirements:**

* Use aiohttp
* Timeout: 3–5 seconds
* Retry: max 2 attempts
* Random User-Agent per request

**Function Signature:**

```python
async def fetch_url(session, url: str) -> dict:
    """
    Returns:
    {
        "status": int,
        "content": str | None,
        "error": str | None
    }
    """
```

---

### 3.2 validator.py

**Responsibilities:**

* Filter invalid responses

**Checks:**

* Status code == 200
* Content-Type contains "text/html"
* Content length < 2MB

**Function Signature:**

```python
def validate_response(response: dict) -> bool:
    ...
```

---

### 3.3 extractor.py

**Primary Tool:**

* trafilatura

**Fallback:**

* BeautifulSoup

**Responsibilities:**

* Extract main content from HTML
* Return clean text

**Function Signature:**

```python
def extract_content(html: str) -> dict:
    """
    Returns:
    {
        "title": str | None,
        "text": str | None
    }
    """
```

**Logic:**

1. Try trafilatura.extract()
2. If empty → fallback to BeautifulSoup
3. Clean whitespace, normalize text

---

### 3.4 fallback.py

**Responsibilities:**

* Handle failed fetches using browser

**Tool:**

* Playwright

**Trigger Conditions:**

* Empty HTML
* Blocked response (403, CAPTCHA)
* Extraction failed

**Function Signature:**

```python
async def fetch_with_browser(url: str) -> str:
    ...
```

---

### 3.5 pipeline.py

**Core orchestrator**

**Responsibilities:**

* Manage full pipeline per URL
* Apply retries + fallback logic

**Function Signature:**

```python
async def process_url(url: str) -> dict:
    """
    Returns:
    {
        "url": str,
        "title": str | None,
        "content": str | None,
        "success": bool
    }
    """
```

**Execution Flow:**

```
1. fetch_url()
2. validate_response()
3. extract_content()

IF failed:
    retry fetch (1x)

IF still failed:
    fetch_with_browser()

IF still failed:
    return success=False
```

---

### 3.6 aggregator.py

**Responsibilities:**

* Run multiple URLs in parallel
* Enforce time budget
* Return partial results

**Function Signature:**

```python
async def process_urls(urls: list[str]) -> list[dict]:
```

**Requirements:**

* Use asyncio.gather()
* Limit concurrency (Semaphore: 5–10)
* Timeout entire batch (~8 sec)

---

## 4. Data Model

### Input

```json
{
  "urls": ["https://example.com/1", "https://example.com/2"]
}
```

### Output

```json
{
  "results": [
    {
      "url": "...",
      "title": "...",
      "content": "...",
      "success": true
    }
  ]
}
```

---

## 5. Error Handling Rules

* Never crash entire pipeline
* Log errors per URL
* Return partial results
* Mark failures explicitly

---

## 6. Performance Constraints

* Max URLs per request: 5–10
* Timeout per request: 3–5 sec
* Total pipeline timeout: ~8 sec
* Max HTML size: 2MB

---

## 7. Anti-Bot (MVP level)

* Random User-Agent rotation
* Basic headers:

```python
headers = {
    "User-Agent": random.choice(USER_AGENTS),
    "Accept-Language": "en-US,en;q=0.9"
}
```

* No proxy required initially

---

## 8. Non-Goals (Do NOT implement yet)

* Proxy pool
* Advanced anti-bot bypass
* Full crawling (depth > 1)
* Persistent caching
* Advanced ranking

---

## 9. Dependencies

* aiohttp
* trafilatura
* beautifulsoup4
* playwright (optional fallback)

---

## 10. Success Criteria

* ≥70% URLs return usable content
* Average response < 8 sec
* No crashes on bad inputs

---

## 11. Future Extensions (Do not implement now)

* Proxy rotation system
* Playwright optimization pool
* Content deduplication
* Domain-level heuristics
* Caching (Redis)

---

# End of Spec

