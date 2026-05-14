from typing import Any, Optional

from logging_config import get_logger
from services.web_scraper.web_scraper import build_web_verification_context

logger = get_logger("services.web_scraper.handler")


def _extract_url_fetcher_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nested_results = payload.get("url_fetcher_results")
    if isinstance(nested_results, dict):
        maybe_results = nested_results.get("results")
        if isinstance(maybe_results, list):
            return maybe_results

    return []


async def handle_web_scraper(payload: dict[str, Any] | None = None) -> Optional[dict]:
    """
    Build web verification context from claims and URL fetcher output.

    Args:
        payload: Dict containing `claims` and URL fetcher results.

    Returns:
        Dict containing merged markdown context and error.
    """
    logger.info("Starting web scraper service")

    claims = (payload or {}).get("claims")
    if not isinstance(claims, list):
        logger.error("No claims list found in payload")
        return {"context": None, "error": "No claims list found in payload"}

    url_fetcher_results = _extract_url_fetcher_results(payload or {})
    if not isinstance(url_fetcher_results, list):
        logger.error("No URL fetcher results found in payload")
        return {"context": None, "error": "No URL fetcher results found in payload"}

    try:
        context = await build_web_verification_context(claims, url_fetcher_results)
        logger.info("Web scraper service completed")
        return {"context": context, "error": None}
    except Exception as e:
        logger.error(f"Web scraper service failed: {str(e)}", exc_info=True)
        return {"context": None, "error": str(e)}
