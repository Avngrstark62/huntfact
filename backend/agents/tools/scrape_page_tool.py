"""Page scraper tool for AI agents to scrape web page content."""

from typing import Union, List, Optional
from agno.tools import Tool
from services.page_scraper import scrape_page
from logging_config import get_logger

logger = get_logger("agents.tools.scrape_page_tool")


async def perform_page_scrape(
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
    try:
        if isinstance(url, str):
            logger.info(f"Scraping single page: {url}")
        else:
            logger.info(f"Scraping {len(url)} pages")
        
        result = await scrape_page(url)
        logger.info("Page scraping completed successfully")
        return result
    except Exception as e:
        logger.error(f"Page scraping failed: {str(e)}", exc_info=True)
        raise


scrape_page_tool = Tool(
    name="scrape_page",
    description="Scrape content from web pages to extract text, title, and other information",
    function=perform_page_scrape,
)
