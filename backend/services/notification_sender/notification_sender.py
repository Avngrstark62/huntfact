from typing import Dict
import logging

from logging_config import get_logger, log_event

logger = get_logger("services.notification_sender.notification_sender")


def _mask_fcm_token(fcm_token: str) -> str:
    token = (fcm_token or "").strip()
    if not token:
        return "<empty>"
    if len(token) <= 10:
        return f"{token[:2]}***{token[-2:]}"
    return f"{token[:6]}***{token[-4:]}"


async def send_notification(hunt_id: int, fcm_token: str) -> Dict[str, str | bool | None]:
    """
    Send lightweight completion notification with hunt id.

    Args:
        hunt_id: Hunt id for fetching result from API later.
        fcm_token: FCM token of the Android device

    Returns:
        Dict with sent status and error.
    """
    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Sending completion notification",
        component="services.notification_sender",
        provider="firebase",
        operation="send_notification",
        hunt_id=hunt_id,
        token_masked=_mask_fcm_token(fcm_token),
    )

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title="Fact check complete",
                body="Your video has been fact checked successfully. Tap to open.",
            ),
            data={
                "type": "fact_check_completed",
                "hunt_id": str(hunt_id),
                "status": "completed",
                "title": "Fact check complete",
                "body": "Your reel is ready. Tap to view the result.",
            },
            token=fcm_token,
        )

        response = messaging.send(message)
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="FCM notification sent",
            component="services.notification_sender",
            provider="firebase",
            operation="send_notification",
            hunt_id=hunt_id,
            response_id=str(response),
        )
        return {"sent": True, "error": None}

    except ImportError:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Firebase Admin SDK not installed",
            component="services.notification_sender",
            provider="firebase",
            operation="send_notification",
            hunt_id=hunt_id,
            error_message="Firebase Admin SDK not installed",
        )
        return {"sent": False, "error": "Firebase Admin SDK not installed"}
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Error sending FCM notification",
            component="services.notification_sender",
            provider="firebase",
            operation="send_notification",
            hunt_id=hunt_id,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"sent": False, "error": str(e)}
