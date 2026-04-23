from typing import Optional
import base64
from logging_config import get_logger
from services.audio_extractor.audio_extractor import extract_audio
from rmq.schemas import TaskMessage
from rmq.constants import TRANSCRIBE
from rmq_redis import job_repository

logger = get_logger("services.audio_extractor.handler")


async def handle_extract_audio(job_id: str) -> Optional[TaskMessage]:
    """
    Extract audio from URL stored in job state.
    
    Extracts audio using the cdn_link from the state and returns updated state
    with audio extraction result, along with the next task message.
    
    Args:
        job_id: Unique job identifier
        job_state: Current job state dict
    
    Returns:
        Tuple of (updated_state, next_task_message)
    """
    logger.info(f"Starting audio extraction for job: {job_id}")
    
    meta = job_repository.get_meta_fields(job_id, ["cdn_link"])
    cdn_link = meta.get("cdn_link")
    
    if not cdn_link:
        logger.error(f"No cdn_link found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Extracting audio from CDN link for job_id: {job_id}")
    
    # Extract audio using the URL
    result = await extract_audio(cdn_link)
    
    # Update job state with audio extraction result
    audio = result.get("audio")
    audio_bytes_b64 = base64.b64encode(audio).decode("utf-8") if audio else None
    job_repository.set_audio(
        job_id,
        audio_bytes_b64,
        result.get("format"),
        result.get("error"),
    )
    
    if result.get("error"):
        logger.error(f"Audio extraction failed for job_id: {job_id}, error: {result.get('error')}")
        return None
    
    logger.info(f"Audio extraction completed for job_id: {job_id}")
    
    # Create transcription task only on success
    task = TaskMessage(
        job_id=job_id,
        step=TRANSCRIBE,
        priority=2,
        payload={}
    )
    
    return task
