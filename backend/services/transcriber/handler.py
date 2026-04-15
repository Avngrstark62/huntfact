from typing import Tuple, Optional
from logging_config import get_logger
from services.transcriber.assemblyai import transcribe_audio
from rmq.schemas import TaskMessage
from rmq.constants import TRANSLATE

logger = get_logger("services.transcriber.handler")


async def handle_transcribe(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Transcribe the extracted audio.
    
    Transcribes audio using the audio_bytes and audio_format from the state
    and returns updated state with transcription result, along with the next task message.
    
    Args:
        job_id: Unique job identifier
        job_state: Current job state dict
    
    Returns:
        Tuple of (updated_state, next_task_message)
    """
    logger.info(f"Starting transcription for job: {job_id}")
    
    # Get audio bytes and format from state
    audio_bytes = job_state.get("audio_bytes")
    audio_format = job_state.get("audio_format")
    
    if not audio_bytes:
        logger.error(f"No audio_bytes found in job state for job_id: {job_id}")
        return job_state, None
    
    if not audio_format:
        logger.error(f"No audio_format found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Transcribing audio for job_id: {job_id}")
    
    # Transcribe audio
    result = await transcribe_audio(audio_bytes, audio_format)
    
    # Update job state with transcription result
    job_state["utterances"] = result.get("utterances") if result else []
    job_state["transcription_language_code"] = result.get("language_code") if result else None
    job_state["transcription_confidence"] = result.get("confidence") if result else None
    job_state["transcription_audio_duration"] = result.get("audio_duration") if result else None
    job_state["transcription_error"] = result.get("error") if result else None
    
    if not result:
        logger.error(f"Transcription failed for job_id: {job_id}")
    else:
        logger.info(f"Transcription completed for job_id: {job_id}")
    
    # Create translation task
    task = TaskMessage(
        job_id=job_id,
        step=TRANSLATE,
        priority=2,
        payload={}
    )
    
    return job_state, task
