from typing import Optional
import base64
from logging_config import get_logger
from services.transcriber.assemblyai import transcribe_audio
from rmq.schemas import TaskMessage
from rmq.constants import TRANSLATE
from rmq_redis import job_repository

logger = get_logger("services.transcriber.handler")


async def handle_transcribe(job_id: str, payload: dict | None = None) -> Optional[TaskMessage]:
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
    
    # Get audio bytes (base64 encoded) and format from state
    audio_bytes_b64, audio_format, audio_error = job_repository.get_audio(job_id)
    
    if not audio_bytes_b64:
        logger.error(f"No audio_bytes found in job state for job_id: {job_id}")
        return None
    
    if not audio_format:
        logger.error(f"No audio_format found in job state for job_id: {job_id}")
        return None

    if audio_error:
        logger.error(f"Audio extraction error found for job_id: {job_id}, error: {audio_error}")
        return None
    
    logger.info(f"Transcribing audio for job_id: {job_id}")
    
    # Decode audio from base64
    try:
        audio_bytes = base64.b64decode(audio_bytes_b64)
    except Exception as e:
        logger.error(f"Failed to decode audio bytes for job_id: {job_id}: {str(e)}", exc_info=True)
        return None
    
    # Transcribe audio
    result = await transcribe_audio(audio_bytes, audio_format)
    
    if not result:
        logger.error(f"Transcription failed for job_id: {job_id}")
        return None

    job_repository.set_utterances(job_id, result.get("utterances") or [])
    job_repository.set_meta_fields(
        job_id,
        {
            "transcription_language_code": result.get("language_code"),
            "transcription_confidence": result.get("confidence"),
            "transcription_audio_duration": result.get("audio_duration"),
            "transcription_error": result.get("error"),
        },
    )
    job_repository.delete_audio(job_id)
    
    logger.info(f"Transcription completed for job_id: {job_id}")
    
    # Create translation task
    task = TaskMessage(
        job_id=job_id,
        step=TRANSLATE,
        priority=3,
        payload={}
    )
    
    return task
