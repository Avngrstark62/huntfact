from typing import Any, Optional
from logging_config import get_logger
from services.notification_sender.notification_sender import send_notification

logger = get_logger("services.notification_sender.handler")


async def handle_notify(payload: dict[str, Any] | None = None) -> Optional[dict]:
    """
    Send completion notification using hunt_id and fcm_token from payload.
    """
    logger.info("Starting notification sender service")

    raw_hunt_id = (payload or {}).get("hunt_id")
    fcm_token = (payload or {}).get("fcm_token")

    if not isinstance(raw_hunt_id, int):
        logger.error("Missing or invalid hunt_id in payload")
        return {"sent": False, "error": "Missing or invalid hunt_id in payload"}

    if not isinstance(fcm_token, str) or not fcm_token.strip():
        logger.error("No valid fcm_token found in payload")
        return {"sent": False, "error": "No valid fcm_token found in payload"}

    send_result = await send_notification(raw_hunt_id, fcm_token)
    if send_result.get("error"):
        logger.error("Notification sender failed: %s", send_result.get("error"))
        return send_result

    logger.info("Notification sent successfully")
    return {"sent": True, "error": None}
