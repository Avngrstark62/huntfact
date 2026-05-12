from typing import Optional

from logging_config import get_logger
from services.url_fetcher.url_fetcher import fetch_urls_for_claims

logger = get_logger("services.url_fetcher.handler")


async def handle_url_fetcher(payload: dict | None = None) -> Optional[dict]:
    """
    Generate verification queries for claims and fetch URLs for each query.

    Args:
        payload: Dict containing claims.

    Returns:
        Dict with url fetch results and error.
    """
    logger.info("Starting URL fetcher service")

    claims = (payload or {}).get("claims")
    if not isinstance(claims, list):
        logger.error("No claims list found in payload")
        return {"results": None, "error": "No claims list found in payload"}

    logger.info(f"Running URL fetcher for {len(claims)} claims")

    try:
        results = await fetch_urls_for_claims(claims)
        logger.info(f"URL fetcher completed with {len(results)} query results")
        return {"results": results, "error": None}
    except Exception as e:
        logger.error(f"URL fetcher failed: {str(e)}", exc_info=True)
        return {"results": None, "error": str(e)}
