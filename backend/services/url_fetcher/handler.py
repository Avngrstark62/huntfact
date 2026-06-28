from typing import Optional
import logging

from logging_config import get_logger, log_event
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
    context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting URL fetcher service",
        component="services.url_fetcher.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        step=context.get("step"),
    )

    claims = (payload or {}).get("claims")
    if not isinstance(claims, list):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No claims list found in payload",
            component="services.url_fetcher.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"results": None, "error": "No claims list found in payload"}

    try:
        results = await fetch_urls_for_claims(claims)
        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="URL fetcher completed",
            component="services.url_fetcher.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            result_summary={"query_result_count": len(results)},
        )
        return {"results": results, "error": None}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="URL fetcher failed",
            component="services.url_fetcher.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"results": None, "error": str(e)}
