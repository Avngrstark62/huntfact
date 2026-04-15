from typing import Tuple, Optional
from logging_config import get_logger
from services.notification_sender.notification_sender import send_notification
from rmq.schemas import TaskMessage

logger = get_logger("services.notification_sender.handler")


async def handle_notify(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Send FCM notification with final result.
    
    Takes result and fcm_token from job state and sends notification to Android app.
    No next task - this is the final step.
    """
    logger.info(f"Starting notification for job: {job_id}")
    
    result = job_state.get("result")
    fcm_token = job_state.get("fcm_token")
    
    if not result:
        logger.error(f"No result found in job state for job_id: {job_id}")
        return job_state, None
    
    if not fcm_token:
        logger.error(f"No fcm_token found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Sending notification for job_id: {job_id}")
    
    await send_notification(result, fcm_token)
    
    logger.info(f"Notification sent for job_id: {job_id}")
    
    return job_state, None
