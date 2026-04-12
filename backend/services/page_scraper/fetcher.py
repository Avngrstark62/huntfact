import asyncio
import aiohttp
import random
from typing import Optional
from logging_config import get_logger

logger = get_logger("services.page_scraper.fetcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict:
    """
    Fetch URL content with timeout and retries.
    
    Returns:
        {
            "status": int,
            "content": str | None,
            "error": str | None
        }
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    max_retries = 2
    timeout = aiohttp.ClientTimeout(total=5)
    
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=timeout, ssl=False) as response:
                content = await response.text()
                return {
                    "status": response.status,
                    "content": content if response.status == 200 else None,
                    "error": None
                }
        except asyncio.TimeoutError:
            error_msg = f"Timeout on attempt {attempt + 1}"
            logger.warning(f"Failed to fetch {url}: {error_msg}")
            if attempt == max_retries - 1:
                return {
                    "status": None,
                    "content": None,
                    "error": error_msg
                }
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to fetch {url}: {error_msg}")
            if attempt == max_retries - 1:
                return {
                    "status": None,
                    "content": None,
                    "error": error_msg
                }
    
    return {
        "status": None,
        "content": None,
        "error": "Failed after retries"
    }
