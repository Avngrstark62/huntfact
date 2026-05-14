from typing import Dict
from logging_config import get_logger

logger = get_logger("services.notification_sender.notification_sender")


async def send_notification(hunt_id: int, fcm_token: str) -> Dict[str, str | bool | None]:
    """
    Send lightweight completion notification with hunt id.

    Args:
        hunt_id: Hunt id for fetching result from API later.
        fcm_token: FCM token of the Android device

    Returns:
        Dict with sent status and error.
    """
    logger.info("Sending completion notification to device: %s", fcm_token)

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title="Fact check complete",
                body="Your video has been fact checked successfully. Tap to open.",
            ),
            data={
                "hunt_id": str(hunt_id),
            },
            token=fcm_token,
        )

        response = messaging.send(message)
        logger.info("FCM notification sent successfully, response: %s", response)
        return {"sent": True, "error": None}

    except ImportError:
        logger.error("Firebase Admin SDK not installed. Install with: pip install firebase-admin")
        return {"sent": False, "error": "Firebase Admin SDK not installed"}
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}", exc_info=True)
        return {"sent": False, "error": str(e)}
