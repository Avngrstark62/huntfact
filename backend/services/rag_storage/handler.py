from typing import Any

from logging_config import get_logger
from services.rag_storage.rag_storage import store_sources_in_rag

logger = get_logger("services.rag_storage.handler")


def _extract_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    direct_sources = payload.get("sources")
    if isinstance(direct_sources, list):
        return direct_sources

    context = payload.get("context")
    if isinstance(context, dict):
        context_sources = context.get("sources")
        if isinstance(context_sources, list):
            return context_sources

    return []


async def handle_rag_storage(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    logger.info("Starting RAG storage service")

    body = payload or {}
    sources = _extract_sources(body)
    if not sources:
        logger.error("No sources list found in payload")
        return {"rag_reference": None, "error": "No sources list found in payload"}

    collection_name = body.get("collection_name")
    if collection_name is not None and not isinstance(collection_name, str):
        logger.error("Invalid collection_name in payload")
        return {"rag_reference": None, "error": "Invalid collection_name in payload"}

    try:
        rag_reference = await store_sources_in_rag(
            sources=sources,
            collection_name=collection_name,
        )
        logger.info("RAG storage service completed")
        return {"rag_reference": rag_reference, "error": None}
    except Exception as e:
        logger.error("RAG storage service failed: %s", str(e), exc_info=True)
        return {"rag_reference": None, "error": str(e)}
