# Production Concern: Scraping Robustness (Tier 1)

Focus: resilience of page extraction when websites are dynamic, blocked, changed, or intermittently failing.

## Major Scraping Robustness Issues

1. **Scraping relies on a single provider path with no fallback extractor** (`backend/services/web_scraper/web_scraper.py`, `backend/services/firecrawl/firecrawl.py`)  
   If Firecrawl behavior degrades for a site pattern (JS-heavy pages, anti-bot defenses, format shifts), evidence collection drops without an alternate scrape path.

2. **Firecrawl request failures are converted to empty content instead of hard failures** (`backend/services/firecrawl/firecrawl.py`)  
   On exceptions, scraper returns `""` and the pipeline continues, which hides extraction breakage and reduces robustness during provider/network incidents.

3. **Web scraper accepts empty markdown as a successful source** (`backend/services/web_scraper/web_scraper.py`)  
   Returned markdown is appended without non-empty validation, so failed/blocked pages can be treated as usable sources and flow deeper into verification.

4. **No retry/backoff strategy for per-URL scrape failures** (`backend/services/web_scraper/web_scraper.py`, `backend/services/firecrawl/firecrawl.py`)  
   Temporary site/provider failures are not retried, increasing false “no evidence” outcomes from short-lived scraping instability.

## Important Scraping Robustness Gaps

5. **Configured Firecrawl API key is not used by scraper client initialization** (`backend/config.py`, `backend/services/firecrawl/firecrawl.py`)  
   `FIRECRAWL_API_KEY` exists in config, but client is created with only `api_url`; environments requiring authenticated scraping can fail broadly.

6. **No explicit handling for common scrape-failure page types** (`backend/services/firecrawl/firecrawl.py`)  
   There are no checks for captcha/login-wall/error-template content, so non-evidence pages may be ingested as normal markdown.

7. **URL-level failure diagnostics are too weak for fast adaptation** (`backend/services/web_scraper/web_scraper.py`, `backend/services/firecrawl/firecrawl.py`)  
   Error details are mostly suppressed (including a commented-out scrape error log), making it hard to detect which sites or patterns are systematically breaking.
