from typing import Dict, Any
import json
from logging_config import get_logger

logger = get_logger("services.notification_sender.notification_sender")


async def send_notification(result: Dict[str, Any], fcm_token: str) -> None:
    """
    Send FCM notification with result to Android app.
    
    Takes the final result and fcm_token, sends a notification to the Android app
    via Firebase Cloud Messaging.
    
    Args:
        result: Final result dictionary with verdict, confidence, explanation, sources
        fcm_token: FCM token of the Android device
    """
    logger.info(f"Sending FCM notification with result to device: {fcm_token}")
    
    try:
        from firebase_admin import messaging
        
        # Parse result if it's a JSON string
        if isinstance(result, str):
            result = json.loads(result)
        
        message = messaging.Message(
            notification=messaging.Notification(
                title="Hunt Fact Analysis Complete",
                body=f"Verdict: {result.get('verdict', 'N/A')}"
            ),
            data={
                "verdict": result.get("verdict", ""),
                "confidence": str(result.get("confidence", "")),
                "explanation": result.get("explanation", ""),
                "sources": json.dumps(result.get("sources", []))
            },
            token=fcm_token,
        )
        
        response = messaging.send(message)
        logger.info(f"FCM notification sent successfully, response: {response}")
        
    except ImportError:
        logger.error("Firebase Admin SDK not installed. Install with: pip install firebase-admin")
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}", exc_info=True)
