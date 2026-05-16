from typing import Any, Optional

from logging_config import get_logger
from services.claim_verifier.claim_verifier import verify_claims_with_context

logger = get_logger("services.claim_verifier.handler")


async def handle_claim_verifier(payload: dict[str, Any] | None = None) -> Optional[dict]:
    logger.info("Starting claim verifier service")

    body = payload or {}
    claims = body.get("claims")
    if not isinstance(claims, list):
        logger.error("No claims list found in payload")
        return {"table": None, "error": "No claims list found in payload"}

    rag_collection_name = body.get("rag_collection_name")
    if not isinstance(rag_collection_name, str):
        rag_reference = body.get("rag_reference")
        if isinstance(rag_reference, dict):
            maybe_collection_name = rag_reference.get("collection_name")
            if isinstance(maybe_collection_name, str):
                rag_collection_name = maybe_collection_name

    if not isinstance(rag_collection_name, str) or not rag_collection_name.strip():
        logger.error("No rag_collection_name found in payload")
        return {"table": None, "error": "No rag_collection_name found in payload"}

    try:
        table = await verify_claims_with_context(claims, rag_collection_name.strip())
        logger.info("Claim verifier service completed")
        return {"table": table, "error": None}
    except Exception as e:
        logger.error(f"Claim verifier service failed: {str(e)}", exc_info=True)
        return {"table": None, "error": str(e)}
