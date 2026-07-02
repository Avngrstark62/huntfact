from typing import Any, Optional
import logging

from logging_config import get_logger, log_event
from s3_client import s3_client
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
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting web scraper service",
        component="services.web_scraper.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    claims = (payload or {}).get("claims")
    if not isinstance(claims, list):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No claims list found in task input",
            component="services.web_scraper.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"context_ref": None, "error": "No claims list found in payload"}

    url_fetcher_results = _extract_url_fetcher_results(payload or {})
    if not isinstance(url_fetcher_results, list):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No URL fetcher results found in task input",
            component="services.web_scraper.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"context_ref": None, "error": "No URL fetcher results found in payload"}

    try:
        context = await build_web_verification_context(claims, url_fetcher_results)
        workflow_id = str(trace_context.get("workflow_id") or "")
        step = str(trace_context.get("step") or "web_scraper")
        task_id = str(trace_context.get("task_id") or "")
        artifact_key = s3_client.build_artifact_key(
            workflow_id=workflow_id,
            step=step,
            task_id=task_id,
            artifact_name="web_context",
            extension="json",
        )
        context_ref = await s3_client.put_json(
            key=artifact_key,
            payload=context,
            metadata={
                "workflow_id": workflow_id,
                "step": step,
                "task_id": task_id,
            },
            tags={
                "workflow_id": workflow_id,
                "step": step,
            },
        )
        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="Web scraper service completed",
            component="services.web_scraper.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"context_ref": context_ref, "error": None}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Web scraper service failed",
            component="services.web_scraper.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"context_ref": None, "error": str(e)}
