import asyncio
from typing import Union, List
from .aggregator import process_urls
from logging_config import get_logger

logger = get_logger("services.page_scraper.page_scraper")


async def scrape_page(url: Union[str, List[str]]) -> dict:
    """
    Simple, clean interface to scrape page content.
    
    Args:
        url: Single URL (str) or list of URLs (List[str])
    
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
                    }
                ]
            }
    """
    if isinstance(url, str):
        # Single URL
        result = await process_urls([url])
        return result["results"][0]
    elif isinstance(url, list):
        # Multiple URLs
        return await process_urls(url)
    else:
        raise ValueError("URL must be a string or list of strings")
