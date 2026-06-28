import logging

from logging_config import get_logger, log_event
from rmq.constants import NOTIFY
from rmq.publisher import publish_task
from rmq.schemas import TaskMessage

logger = get_logger("services.notification_sender.notify_publish")


async def publish_notify_best_effort(
    hunt_id: int,
    fcm_token: str,
    context: dict | None = None,
) -> None:
    try:
        payload_context = dict(context or {})
        payload_context["hunt_id"] = hunt_id
        await publish_task(
            TaskMessage(
                step=NOTIFY,
                priority=10,
                payload={
                    "fcm_token": fcm_token,
                    "hunt_id": hunt_id,
                    "context": payload_context,
                },
            )
        )
    except Exception as notify_error:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.publish.failed",
            status="failed",
            message="Best-effort notify publish failed",
            component="services.notification_sender.notify_publish",
            hunt_id=hunt_id,
            workflow_id=payload_context.get("workflow_id"),
            request_id=payload_context.get("request_id"),
            error_type=type(notify_error).__name__,
            error_message=str(notify_error),
            exc_info=True,
        )
