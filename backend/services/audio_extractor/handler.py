from typing import Tuple, Optional
from logging_config import get_logger
from services.audio_extractor.audio_extractor import extract_audio
from rmq.schemas import TaskMessage
from rmq.constants import TRANSCRIBE

logger = get_logger("services.audio_extractor.handler")


async def handle_extract_audio(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
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
    
    # Get cdn_link from state
    cdn_link = job_state.get("cdn_link")
    
    if not cdn_link:
        logger.error(f"No cdn_link found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Extracting audio from CDN link for job_id: {job_id}")
    
    # Extract audio using the URL
    result = await extract_audio(cdn_link)
    
    # Update job state with audio extraction result
    job_state["audio_bytes"] = result.get("audio")
    job_state["audio_format"] = result.get("format")
    job_state["audio_error"] = result.get("error")
    
    if result.get("error"):
        logger.error(f"Audio extraction failed for job_id: {job_id}, error: {result.get('error')}")
    else:
        logger.info(f"Audio extraction completed for job_id: {job_id}")
    
    # Create transcription task
    task = TaskMessage(
        job_id=job_id,
        step=TRANSCRIBE,
        priority=2,
        payload={}
    )
    
    return job_state, task
