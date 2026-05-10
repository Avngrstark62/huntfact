from typing import Optional
import base64
from logging_config import get_logger
from services.transcriber.assemblyai import transcribe_audio

logger = get_logger("services.transcriber.handler")


async def handle_transcribe(payload: dict | None = None) -> Optional[dict]:
    """
    Transcribe extracted audio from payload.

    Args:
        payload: dict containing audio_bytes_b64 and audio_format.

    Returns:
        dict containing transcript_text and error.
    """
    logger.info("Starting transcription")
    
    audio_bytes_b64 = (payload or {}).get("audio_bytes_b64")
    audio_format = (payload or {}).get("audio_format")
    
    if not audio_bytes_b64:
        logger.error("No audio_bytes_b64 found in payload")
        return {"transcript_text": None, "error": "No audio_bytes_b64 found in payload"}
    
    if not audio_format:
        logger.error("No audio_format found in payload")
        return {"transcript_text": None, "error": "No audio_format found in payload"}
    
    logger.info("Transcribing audio")
    
    # Decode audio from base64
    try:
        audio_bytes = base64.b64decode(audio_bytes_b64)
    except Exception as e:
        logger.error(f"Failed to decode audio bytes: {str(e)}", exc_info=True)
        return {"transcript_text": None, "error": f"Failed to decode audio bytes: {str(e)}"}
    
    # Transcribe audio
    result = await transcribe_audio(audio_bytes, audio_format)
    
    if not result:
        logger.error("Transcription failed")
        return {"transcript_text": None, "error": "Transcription failed"}
    
    logger.info("Transcription completed")

    return {"transcript_text": result, "error": None}
