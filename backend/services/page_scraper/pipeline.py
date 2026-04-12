import asyncio
import aiohttp
from .fetcher import fetch_url
from .validator import validate_response
from .extractor import extract_content
from logging_config import get_logger

logger = get_logger("services.page_scraper.pipeline")


async def process_url(url: str, session: aiohttp.ClientSession = None) -> dict:
    """
    Process single URL through the complete pipeline.
    
    Returns:
        {
            "url": str,
            "title": str | None,
            "content": str | None,
            "success": bool
        }
    """
    should_close_session = False
    
    try:
        if session is None:
            session = aiohttp.ClientSession()
            should_close_session = True
        
        # Fetch URL
        response = await fetch_url(session, url)
        
        # Validate response
        if not validate_response(response):
            logger.warning(f"Validation failed for {url}")
            return {
                "url": url,
                "title": None,
                "content": None,
                "success": False
            }
        
        # Extract content
        extracted = extract_content(response["content"])
        
        if not extracted.get("text"):
            logger.warning(f"Content extraction failed for {url}")
            return {
                "url": url,
                "title": extracted.get("title"),
                "content": None,
                "success": False
            }
        
        return {
            "url": url,
            "title": extracted.get("title"),
            "content": extracted.get("text"),
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Pipeline error for {url}: {str(e)}")
        return {
            "url": url,
            "title": None,
            "content": None,
            "success": False
        }
    
    finally:
        if should_close_session:
            await session.close()
