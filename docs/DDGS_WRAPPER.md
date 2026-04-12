## **DDGS Wrapper - A Metasearch Engine**

**What it is:** A sophisticated web scraping and search aggregation library that acts as a **metasearch engine**—pooling results from multiple search providers (DuckDuckGo, Google, Bing, Brave, Wikipedia, etc.) simultaneously to give you more comprehensive and diverse search results.

---

## **Core Features & Functionalities:**

### **1. Multi-Engine Search Aggregation**
- **Auto-mode (default):** Queries all available search engines in parallel and combines results
- **Selective backends:** Can target specific engines (e.g., `backend='google'`) or combinations (`backend='duckduckgo,bing'`)
- **Available engines:** DuckDuckGo, Google, Bing, Brave, Wikipedia, Grokipedia, Yahoo, Yandex, Mojeek
- **Smart prioritization:** Wikipedia and Grokipedia results bubble to the top; results are ranked by relevance

### **2. Multiple Search Categories**
- **Text search** (web pages)
- **Images search**
- **News search**
- **Videos search**
- **Books search**

### **3. Advanced Search Parameters**
- **Region support:** Localized searches (e.g., `us-en`, `uk-en`, `ru-ru`)
- **Safe search levels:** `on`, `moderate`, or `off`
- **Time filtering:** `d` (day), `w` (week), `m` (month), `y` (year)
- **Pagination:** Page-based result navigation
- **Result limiting:** Control max results returned

### **4. Result Processing Pipeline**
- **Deduplication:** Eliminates duplicate results from multiple engines using cache fields (href, image, url, embed_url)
- **Frequency ranking:** Results appearing in multiple engines rank higher (using a Counter)
- **Query-based ranking:** `SimpleFilterRanker` ranks results by:
  - Wikipedia results first
  - Results matching both title AND body/description
  - Title-only matches
  - Body-only matches
  - Results with no matches
- **Text normalization:** Cleans HTML, unescapes entities, normalizes Unicode, collapses whitespace

### **5. Robust HTTP Layer**
- **primp-based client:** Modern HTTP client with browser impersonation (`impersonate='random'`)
- **Proxy support:** HTTP, HTTPS, SOCKS5 protocols
- **SSL verification:** Can verify, skip, or use custom PEM certificates
- **Configurable timeouts:** Request-level timeout control
- **Error handling:** Custom exceptions (`DDGSException`, `TimeoutException`, `RatelimitException`)

### **6. Content Extraction**
- **`extract()` method:** Fetches full page content and converts to multiple formats:
  - `text_markdown` (page content as markdown)
  - `text_plain` (plain text)
  - `text_rich` (rich formatted text)
  - `text` (raw HTML)
  - `content` (raw bytes)

### **7. Concurrent Architecture**
- **ThreadPoolExecutor:** Parallel querying across engines (respects max_workers)
- **Smart concurrency:** Adapts thread count based on results needed
- **First-exception handling:** Stops waiting if an engine fails quickly, allowing fallbacks

### **8. Type-Safe Result Objects**
Structured result dataclasses:
- `TextResult` (title, href, body)
- `ImagesResult` (image metadata)
- `NewsResult` (date, source, publisher)
- `VideosResult` (duration, embed_url, uploader info)
- `BooksResult` (author, publisher info)

### **9. Main API Entry Points**
```python
# Simple function-based API (most common)
from ddgs_wrapper import search_web
results = search_web("python", max_results=5, backend="auto")

# Context manager API
from ddgs_wrapper import DDGS
with DDGS(proxy=..., timeout=...) as ddgs:
    results = ddgs.text("query")
    images = ddgs.images("query")
```

---

## **Key Design Patterns:**

1. **Lazy loading:** DDGS class uses a proxy metaclass to defer initialization
2. **Engine caching:** Initializes search engines once and reuses them
3. **Aggregation pattern:** `ResultsAggregator` deduplicates and ranks results
4. **Template pattern:** `BaseSearchEngine` abstract class defines how each engine works
5. **Pluggable architecture:** New search engines can be added by subclassing `BaseSearchEngine`
