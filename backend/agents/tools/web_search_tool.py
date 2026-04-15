"""Web search tool for AI agents to perform web searches."""

from typing import Any, Optional
from agno.tools import tool
from services.web_searcher import search_web
from agents.tools.scrape_page_tool import _scrape_page_impl
from logging_config import get_logger

logger = get_logger("agents.tools.web_search_tool")


async def _web_search_impl(
    query: str,
    max_results: int = 10,
    region: str = "in-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    page: int = 1,
    backend: str = "duckduckgo",
    proxy: Optional[str] = None,
    timeout: Optional[int] = 10,
    verify: bool = True,
) -> list[dict[str, Any]]:
    """
    Internal implementation for web search.
    """
    try:
        logger.info(f"Web search initiated - Query: '{query}'")
        logger.debug(f"Parameters: max_results={max_results}, region={region}, backend={backend}")
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
        logger.info(f"Web search completed - Found {len(results)} results")
        logger.debug(f"Results: {results}")
        return results
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}", exc_info=True)
        raise


@tool
async def web_search(
    query: str,
) -> list[dict[str, Any]]:
    """
    Perform a web search and return results.
    
    Args:
        query: The search query string (required).
    
    Returns:
        List of search results with 'title', 'href', and 'body' fields.
    """
    return await _web_search_impl(
        query=query,
        max_results=10,
        region="in-en",
        safesearch="moderate",
        timelimit=None,
        page=1,
        backend="duckduckgo",
        proxy=None,
        timeout=10,
        verify=True,
    )
