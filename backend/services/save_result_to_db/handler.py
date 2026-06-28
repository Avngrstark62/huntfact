from typing import Any, Optional
import logging

from logging_config import get_logger, log_event
from services.save_result_to_db.save_result_to_db import save_result_to_db

logger = get_logger("services.save_result_to_db.handler")


async def handle_save_result_to_db(payload: dict[str, Any] | None = None) -> Optional[dict]:
    """
    Save claim-verifier table in DB using explicit payload input.

    Expected payload:
        {
            "hunt_id": <int>,
            "table": <dict>
        }
    """
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting save_result_to_db service",
        component="services.save_result_to_db.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    raw_hunt_id = (payload or {}).get("hunt_id")
    table = (payload or {}).get("table")

    if not isinstance(raw_hunt_id, int):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Missing or invalid hunt_id in payload",
            component="services.save_result_to_db.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"saved": None, "error": "Missing or invalid hunt_id in payload"}

    if not isinstance(table, dict):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Missing or invalid table in payload",
            component="services.save_result_to_db.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"saved": None, "error": "Missing or invalid table in payload"}

    try:
        saved = await save_result_to_db(raw_hunt_id, table)
        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="save_result_to_db service completed",
            component="services.save_result_to_db.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=raw_hunt_id,
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"saved": saved, "error": None}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="save_result_to_db service failed",
            component="services.save_result_to_db.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=raw_hunt_id if isinstance(raw_hunt_id, int) else trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"saved": None, "error": str(e)}
