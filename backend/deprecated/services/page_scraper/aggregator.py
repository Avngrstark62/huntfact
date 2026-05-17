import asyncio
import aiohttp
from typing import List
from .pipeline import process_url
from logging_config import get_logger

logger = get_logger("services.page_scraper.aggregator")


async def process_urls(urls: List[str], timeout: int = 8, max_concurrent: int = 5) -> dict:
    """
    Process multiple URLs in parallel with concurrency limits.
    
    Args:
        urls: List of URLs to process
        timeout: Total timeout in seconds
        max_concurrent: Maximum concurrent requests
    
    Returns:
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
    if not urls:
        return {"results": []}
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(session: aiohttp.ClientSession, url: str):
        async with semaphore:
            return await process_url(url, session)
    
    try:
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [process_with_semaphore(session, url) for url in urls]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            # Handle exceptions in results
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {str(result)}")
                    processed_results.append({
                        "url": "unknown",
                        "title": None,
                        "content": None,
                        "success": False
                    })
                else:
                    processed_results.append(result)
            
            return {"results": processed_results}
    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout processing {len(urls)} URLs")
        return {
            "results": [
                {
                    "url": url,
                    "title": None,
                    "content": None,
                    "success": False
                }
                for url in urls
            ]
        }
    except Exception as e:
        logger.error(f"Aggregator error: {str(e)}")
        return {
            "results": [
                {
                    "url": url,
                    "title": None,
                    "content": None,
                    "success": False
                }
                for url in urls
            ]
        }
