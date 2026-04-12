"""Web search tool for AI agents to perform web searches."""

from typing import Any, Optional
from agno.tools import Tool
from services.web_searcher import search_web
from logging_config import get_logger

logger = get_logger("agents.tools.web_search_tool")


def perform_web_search(
    query: str,
    max_results: int = 10,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    page: int = 1,
    backend: str = "auto",
    proxy: Optional[str] = None,
    timeout: Optional[int] = 5,
    verify: bool = True,
) -> list[dict[str, Any]]:
    """
    Perform a web search and return results.
    
    Args:
        query: The search query string (required).
        max_results: Maximum number of results to return. Defaults to 10.
        region: Region for localized search (e.g., 'us-en', 'uk-en', 'ru-ru'). Defaults to 'us-en'.
        safesearch: Safe search setting - 'on', 'moderate', or 'off'. Defaults to 'moderate'.
        timelimit: Filter results by time - 'd' (day), 'w' (week), 'm' (month), 'y' (year). Defaults to None.
        page: Page number for pagination (1-based). Defaults to 1.
        backend: Which search engine to use - 'auto', 'duckduckgo', 'bing', 'google', 'brave', or comma-separated list. Defaults to 'auto'.
        proxy: Proxy server URL (e.g., 'socks5h://127.0.0.1:9150'). Defaults to None.
        timeout: HTTP request timeout in seconds. Defaults to 5.
        verify: SSL certificate verification. Defaults to True.
    
    Returns:
        List of search results with 'title', 'href', and 'body' fields.
    """
    try:
        logger.info(f"Performing web search with query: {query}")
        results = search_web(
            query=query,
            max_results=max_results,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            page=page,
            backend=backend,
            proxy=proxy,
            timeout=timeout,
            verify=verify,
        )
        logger.info(f"Web search completed, found {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}", exc_info=True)
        raise


web_search_tool = Tool(
    name="web_search",
    description="Search the web for information using multiple search engines",
    function=perform_web_search,
)
