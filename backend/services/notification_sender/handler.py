from typing import Optional
from logging_config import get_logger
from services.notification_sender.notification_sender import send_notification
from rmq.schemas import TaskMessage
from rmq_redis import job_repository

logger = get_logger("services.notification_sender.handler")


async def handle_notify(job_id: str, payload: dict | None = None) -> Optional[TaskMessage]:
    """
    Send FCM notification with final result.
    
    Takes result and fcm_token from job state and sends notification to Android app.
    No next task - this is the final step.
    """
    logger.info(f"Starting notification for job: {job_id}")
    
    result = job_repository.get_result(job_id)
    fcm_token = job_repository.get_meta_fields(job_id, ["fcm_token"]).get("fcm_token")
    
    if not result:
        logger.error(f"No result found in job state for job_id: {job_id}")
        return None
    
    if not fcm_token:
        logger.error(f"No fcm_token found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Sending notification for job_id: {job_id}")
    
    await send_notification(result, fcm_token)
    
    logger.info(f"Notification sent for job_id: {job_id}")
    
    return None
