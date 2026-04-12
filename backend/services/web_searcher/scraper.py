"""Simple interface for DuckDuckGo web scraping.

This module provides a straightforward function-based API for performing web searches
using the DDGS (Dux Distributed Global Search) engine with DuckDuckGo as the primary backend.

Features:
- Text web search with multiple fallback engines (DuckDuckGo, Bing, Google, Brave, etc.)
- Full support for search parameters (region, safe search, time limits, pagination)
- Result deduplication and ranking
- Proxy support
- SSL certificate verification control
- Configurable timeouts
"""

from typing import Any

from services.web_searcher.ddgs import DDGS


def search_web(
    query: str,
    max_results: int | None = 10,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    page: int = 1,
    backend: str = "auto",
    proxy: str | None = None,
    timeout: int | None = 5,
    verify: bool | str = True,
) -> list[dict[str, Any]]:
    """Perform a web text search using DDGS.

    This is the primary interface for web scraping. It aggregates results from
    multiple search engines, starting with DuckDuckGo, and falls back to other
    engines (Bing, Google, Brave, Wikipedia, etc.) for better coverage.

    Args:
        query: The search query string (required).
        max_results: Maximum number of results to return. Defaults to 10.
        region: Region for localized search (e.g., 'us-en', 'uk-en', 'ru-ru', etc.).
            Defaults to 'us-en'.
        safesearch: Safe search setting - 'on', 'moderate', or 'off'.
            Defaults to 'moderate'.
        timelimit: Filter results by time - 'd' (day), 'w' (week), 'm' (month), 'y' (year).
            Defaults to None (no time limit).
        page: Page number for pagination (1-based). Defaults to 1.
        backend: Specify which search engine to use:
            - 'auto' (default): Uses all available engines (DuckDuckGo, Bing, Google, etc.)
            - 'duckduckgo': DuckDuckGo only
            - 'bing': Bing only
            - 'google': Google only
            - 'brave': Brave only
            - Or comma-separated list: 'duckduckgo,bing,google'
        proxy: Proxy server URL (supports http/https/socks5).
            Example: 'http://user:pass@example.com:3128' or 'socks5h://127.0.0.1:9150'.
            Defaults to None. Can also be set via DDGS_PROXY environment variable.
        timeout: HTTP request timeout in seconds. Defaults to 5.
        verify: SSL certificate verification.
            - True (default): Verify SSL certificates
            - False: Skip SSL verification
            - str: Path to PEM certificate file

    Returns:
        List of dictionaries containing search results with the following fields:
            - 'title': The page title or heading
            - 'href': The page URL
            - 'body': Brief description or snippet of the page content

    Raises:
        DDGSException: If the search fails or no results are found.
        TimeoutException: If the search times out.

    Examples:
        >>> # Basic search
        >>> results = search_web("python programming", max_results=5)
        >>> for result in results:
        ...     print(f"{result['title']}: {result['href']}")

        >>> # Search with time limit and safe search off
        >>> results = search_web(
        ...     "python 3.11",
        ...     max_results=10,
        ...     timelimit="m",  # Last month only
        ...     safesearch="off"
        ... )

        >>> # Search with specific backend
        >>> results = search_web("tech news", backend="duckduckgo")

        >>> # Search with proxy
        >>> results = search_web(
        ...     "query",
        ...     proxy="socks5h://127.0.0.1:9150"
        ... )

        >>> # Search with pagination
        >>> page1 = search_web("python", page=1, max_results=10)
        >>> page2 = search_web("python", page=2, max_results=10)
    """
    ddgs = DDGS(proxy=proxy, timeout=timeout, verify=verify)
    return ddgs.text(
        query,
        region=region,
        safesearch=safesearch,
        timelimit=timelimit,
        max_results=max_results,
        page=page,
        backend=backend,
    )


__all__ = ["search_web"]
