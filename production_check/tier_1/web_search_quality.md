# Production Concern: Web Search Quality (Tier 1)

Focus: whether retrieved sources are relevant, trustworthy, and sufficient for accurate verification.

## Major Web Search Quality Issues

1. **Search requests do not constrain engines, categories, language, or recency** (`backend/services/url_fetcher/url_fetcher.py`)  
   Queries are sent as only `q` + `format=json`, so ranking can drift toward low-quality, stale, or region-mismatched pages that weaken evidence quality.

2. **Result normalization drops useful ranking context (snippet/source metadata)** (`backend/services/url_fetcher/url_fetcher.py`)  
   Pipeline keeps only `title` and `url`, removing snippet/body/provider signals that are needed to judge whether a result actually supports a claim before scraping.

3. **URL selector evaluates candidates without page-level evidence preview** (`backend/services/web_scraper/web_scraper.py`)  
   LLM selection is based on `query + title + url` only, which increases false-positive source selection (good-looking titles, weak content).

4. **No explicit source credibility policy before selection/scraping** (`backend/services/web_scraper/web_scraper.py`)  
   There is no allow/deny/domain-authority gate, so low-trust or spammy domains can enter the verification context and distort verdicts.

## Important Web Search Quality Gaps

5. **Diversity controls are missing across selected sources** (`backend/services/web_scraper/web_scraper.py`)  
   Selection has no domain-diversity requirement, so multiple near-duplicate pages from the same ecosystem can dominate context and create false confidence.

6. **Scrape failures are silently discarded, reducing evidence coverage quality** (`backend/services/web_scraper/web_scraper.py`, `backend/services/firecrawl/firecrawl.py`)  
   Failed/empty pages are skipped without preserving failure reason in context, so downstream verifier may operate on thinner evidence than expected.

7. **No minimum evidence bar before handing off to verification** (`backend/orchestrator.py`, `backend/services/web_scraper/web_scraper.py`)  
   Verification continues as long as at least one source exists, even if coverage is shallow; this raises risk of low-quality “verifiable-looking” outputs.
