from typing import Any, Optional

from logging_config import get_logger
from services.claim_verifier.claim_verifier import verify_claims_with_context

logger = get_logger("services.claim_verifier.handler")


async def handle_claim_verifier(payload: dict[str, Any] | None = None) -> Optional[dict]:
    logger.info("Starting claim verifier service")

    claims = (payload or {}).get("claims")
    if not isinstance(claims, list):
        logger.error("No claims list found in payload")
        return {"table": None, "error": "No claims list found in payload"}

    context = (payload or {}).get("context")
    if not isinstance(context, dict):
        logger.error("No context dict found in payload")
        return {"table": None, "error": "No context dict found in payload"}

    try:
        table = await verify_claims_with_context(claims, context)
        logger.info("Claim verifier service completed")
        return {"table": table, "error": None}
    except Exception as e:
        logger.error(f"Claim verifier service failed: {str(e)}", exc_info=True)
        return {"table": None, "error": str(e)}
