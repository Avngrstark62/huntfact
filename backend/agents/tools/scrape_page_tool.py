"""Page scraper tool for AI agents to scrape web page content."""

from typing import Union, List, Optional
from agno.tools import tool
from services.page_scraper import scrape_page as scrape_page_impl
from logging_config import get_logger

logger = get_logger("agents.tools.scrape_page_tool")


async def _scrape_page_impl(
    url: Union[str, List[str]],
) -> Union[dict, dict]:
    """
    Internal implementation for scraping content from one or more web pages.
    """
    try:
        if isinstance(url, str):
            logger.info(f"Page scrape initiated - URL: {url}")
        else:
            logger.info(f"Page scrape initiated - Scraping {len(url)} URLs")
            logger.debug(f"URLs: {url}")
        
        result = await scrape_page_impl(url)
        logger.info(f"Page scrape completed successfully")
        logger.debug(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Page scrape failed: {str(e)}", exc_info=True)
        raise


@tool
async def scrape_page(
    url: Union[str, List[str]],
) -> Union[dict, dict]:
    """
    Scrape content from one or more web pages.
    
    Args:
        url: Single URL (str) or list of URLs (List[str]) to scrape.
    
    Returns:
        For single URL:
            {
                "url": str,
                "title": str | None,
                "content": str | None,
                "success": bool
            }
        
        For multiple URLs:
            {
                "results": [
                    {
                        "url": str,
                        "title": str | None,
                        "content": str | None,
                        "success": bool
                    },
                    ...
                ]
            }
    """
    return await _scrape_page_impl(url)
