from typing import Optional

from logging_config import get_logger
from services.claim_extractor.claim_extractor import extract_claim_clusters

logger = get_logger("services.claim_extractor.handler")


async def handle_extract_claim_clusters(payload: dict | None = None) -> Optional[dict]:
    """
    Extract clustered objective claims from content.

    Args:
        payload: Dict containing content.

    Returns:
        Dict with claim clusters and error.
    """
    logger.info("Starting claim cluster extraction")

    content = (payload or {}).get("content")

    if not content:
        logger.error("No content found in payload")
        return {"clusters": None, "error": "No content found in payload"}

    logger.info(f"Extracting claim clusters from content ({len(content)} chars)")

    clusters = await extract_claim_clusters(content)

    logger.info(f"Claim cluster extraction completed ({len(clusters)} clusters)")

    return {"clusters": clusters, "error": None}
