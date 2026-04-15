from logging_config import get_logger
from redis import get_job_data, update_job_data
from services.audio_extractor.audio_extractor import extract_audio
from rmq.publisher import publish_task
from rmq.schemas import TaskMessage
from rmq.constants import TRANSCRIBE

logger = get_logger("services.audio_extractor.handler")


async def handle_extract_audio(job_id: str) -> None:
    """
    Extract audio from URL stored in Redis job state.
    
    Fetches the job state from Redis, retrieves the cdn_link,
    extracts audio using the URL, and updates the job state with the result.
    Publishes a TRANSCRIBE task when complete.
    
    Args:
        job_id: Unique job identifier
    """
    logger.info(f"Starting audio extraction for job: {job_id}")
    
    # Fetch job state from Redis
    job_state = get_job_data(job_id)
    
    if job_state is None:
        logger.error(f"Job state not found in Redis for job_id: {job_id}")
        return
    
    # Get cdn_link from state
    cdn_link = job_state.get("cdn_link")
    
    if not cdn_link:
        logger.error(f"No cdn_link found in job state for job_id: {job_id}")
        return
    
    logger.info(f"Extracting audio from CDN link for job_id: {job_id}")
    
    # Extract audio using the URL
    result = extract_audio(cdn_link)
    
    # Update job state with audio extraction result
    job_state["audio_bytes"] = result.get("audio")
    job_state["audio_format"] = result.get("format")
    job_state["audio_error"] = result.get("error")
    
    update_job_data(job_id, job_state)
    
    if result.get("error"):
        logger.error(f"Audio extraction failed for job_id: {job_id}, error: {result.get('error')}")
    else:
        logger.info(f"Audio extraction completed for job_id: {job_id}")
    
    # Publish transcription task
    task = TaskMessage(
        job_id=job_id,
        step=TRANSCRIBE,
        priority=2,
        payload={}
    )
    
    await publish_task(task)
    logger.info(f"Transcription task published for job_id: {job_id}")
