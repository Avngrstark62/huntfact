from typing import Any, Optional
import logging
from logging_config import get_logger, log_event
from services.notification_sender.notification_sender import send_notification

logger = get_logger("services.notification_sender.handler")


async def handle_notify(payload: dict[str, Any] | None = None) -> Optional[dict]:
    """
    Send completion notification using hunt_id and fcm_token from payload.
    """
    trace_context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    trace_context = trace_context if isinstance(trace_context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting notification sender service",
        component="services.notification_sender.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=trace_context.get("hunt_id"),
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
        step=trace_context.get("step"),
    )

    raw_hunt_id = (payload or {}).get("hunt_id")
    fcm_token = (payload or {}).get("fcm_token")

    if not isinstance(raw_hunt_id, int):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Missing or invalid hunt_id in payload",
            component="services.notification_sender.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=trace_context.get("hunt_id"),
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"sent": False, "error": "Missing or invalid hunt_id in payload"}

    if not isinstance(fcm_token, str) or not fcm_token.strip():
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No valid fcm_token found in payload",
            component="services.notification_sender.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=raw_hunt_id,
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
        )
        return {"sent": False, "error": "No valid fcm_token found in payload"}

    send_result = await send_notification(raw_hunt_id, fcm_token)
    if send_result.get("error"):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Notification sender failed",
            component="services.notification_sender.handler",
            workflow_id=trace_context.get("workflow_id"),
            hunt_id=raw_hunt_id,
            request_id=trace_context.get("request_id"),
            task_id=trace_context.get("task_id"),
            error_message=str(send_result.get("error")),
        )
        return send_result

    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Notification sent successfully",
        component="services.notification_sender.handler",
        workflow_id=trace_context.get("workflow_id"),
        hunt_id=raw_hunt_id,
        request_id=trace_context.get("request_id"),
        task_id=trace_context.get("task_id"),
    )
    return {"sent": True, "error": None}
