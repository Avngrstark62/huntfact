"""
Audio transcription service using Deepgram API.
Handles audio bytes and returns full transcription response with diarization.
"""

import io
from typing import Optional, Dict, Any

from deepgram import DeepgramClient

from config import settings
from logging_config import get_logger

logger = get_logger("services.transcriber.transcriber")


def transcribe_audio(audio_bytes: bytes, fmt: str) -> Optional[Dict[str, Any]]:
    """
    Transcribe audio bytes using Deepgram API with diarization.
    
    Args:
        audio_bytes: raw bytes from extract_audio
        fmt: audio format ("aac" or "mp3")
    
    Returns:
        full Deepgram response as dict or None if transcription fails
    
    Raises:
        ValueError: if audio_bytes is empty or invalid
        Exception: if Deepgram API call fails
    """
    if not audio_bytes:
        error_msg = "audio_bytes cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not fmt or fmt not in ("aac", "mp3"):
        error_msg = f"Invalid audio format: {fmt}. Must be 'aac' or 'mp3'"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info(f"Starting transcription for {fmt} audio ({len(audio_bytes)} bytes)")
        
        # Initialize Deepgram client
        client = DeepgramClient(settings.deepgram_api_key)

        options = {
                "model": "nova-2",
                "smart_format": True,
                "punctuate": True,
                "diarize": True,
                }
        
        # Deepgram expects buffer input
        response = client.listen.prerecorded.v("1").transcribe(
            {"buffer": audio_bytes},
            options
        )
        
        result = response.to_dict()
        
        logger.info("Transcription completed successfully")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Deepgram API error: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        raise
