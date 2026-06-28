from typing import Optional
import logging

from logging_config import get_logger, log_event
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
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting claim cluster extraction",
        component="services.claim_extractor.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    content = (payload or {}).get("content")

    if not content:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No content found in payload",
            component="services.claim_extractor.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"clusters": None, "error": "No content found in payload"}

    clusters = await extract_claim_clusters(content)

    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Claim cluster extraction completed",
        component="services.claim_extractor.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        result_summary={"cluster_count": len(clusters)},
    )

    return {"clusters": clusters, "error": None}
