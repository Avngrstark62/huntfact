# Page Scraper Service

A lightweight, async page scraping service for extracting clean content from URLs.

## Usage

### Single URL

```python
from services.page_scraper import scrape_page

result = await scrape_page("https://example.com")

# Returns:
# {
#     "url": "https://example.com",
#     "title": "Page Title",
#     "content": "Extracted page content...",
#     "success": true
# }
```

### Multiple URLs

```python
from services.page_scraper import scrape_page

results = await scrape_page([
    "https://example.com/1",
    "https://example.com/2",
    "https://example.com/3"
])

# Returns:
# {
#     "results": [
#         {"url": "...", "title": "...", "content": "...", "success": true},
#         {"url": "...", "title": "...", "content": "...", "success": false},
#         ...
#     ]
# }
```

## Features

- **Async Processing**: Non-blocking HTTP requests using aiohttp
- **Concurrency Control**: Limits concurrent requests (default: 5)
- **Content Extraction**: Trafilatura for primary extraction, BeautifulSoup fallback
- **Timeout Protection**: 8-second total timeout for batch processing
- **Error Resilience**: Partial success allowed, graceful error handling
- **User-Agent Rotation**: Random user agents to avoid detection

## Pipeline

1. **Fetch**: Async HTTP GET with retries and timeouts
2. **Validate**: Check status code, content size
3. **Extract**: Primary extraction via trafilatura, fallback to BeautifulSoup
4. **Aggregate**: Run multiple URLs in parallel with concurrency limits
