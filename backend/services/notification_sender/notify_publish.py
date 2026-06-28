from logging_config import get_logger
from rmq.constants import NOTIFY
from rmq.publisher import publish_task
from rmq.schemas import TaskMessage

logger = get_logger("services.notification_sender.notify_publish")


async def publish_notify_best_effort(hunt_id: int, fcm_token: str) -> None:
    try:
        await publish_task(
            TaskMessage(
                step=NOTIFY,
                priority=10,
                payload={
                    "fcm_token": fcm_token,
                    "hunt_id": hunt_id,
                },
            )
        )
    except Exception as notify_error:
        logger.error(
            "Best-effort notify publish failed for hunt_id=%s: %s",
            hunt_id,
            str(notify_error),
            exc_info=True,
        )
