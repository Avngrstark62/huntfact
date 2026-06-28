from typing import Any
import logging

from logging_config import get_logger, log_event
from services.rag_storage.rag_storage import store_sources_in_rag

logger = get_logger("services.rag_storage.handler")


def _extract_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    direct_sources = payload.get("sources")
    if isinstance(direct_sources, list):
        return direct_sources

    return []


async def handle_rag_storage(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting RAG storage service",
        component="services.rag_storage.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    body = payload or {}
    sources = _extract_sources(body)
    if not sources:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No sources list found in payload",
            component="services.rag_storage.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"rag_reference": None, "error": "No sources list found in payload"}

    collection_name = body.get("collection_name")
    if collection_name is not None and not isinstance(collection_name, str):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Invalid collection_name in payload",
            component="services.rag_storage.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"rag_reference": None, "error": "Invalid collection_name in payload"}

    try:
        rag_reference = await store_sources_in_rag(
            sources=sources,
            collection_name=collection_name,
        )
        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="RAG storage service completed",
            component="services.rag_storage.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            result_summary={"collection_name": rag_reference.get("collection_name"), "chunk_count": rag_reference.get("chunk_count")},
        )
        return {"rag_reference": rag_reference, "error": None}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="RAG storage service failed",
            component="services.rag_storage.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"rag_reference": None, "error": str(e)}
