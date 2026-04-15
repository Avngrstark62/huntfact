"""
Audio transcription service using OpenAI's Whisper API.
Handles audio bytes and returns transcribed text.
"""

import io
from typing import Optional

from openai import OpenAI, OpenAIError

from config import settings
from logging_config import get_logger

logger = get_logger("services.transcriber.transcriber")


def transcribe_audio(audio_bytes: bytes, fmt: str) -> Optional[str]:
    """
    Transcribe audio bytes to text using OpenAI's Whisper API.

    Args:
        audio_bytes: raw bytes from extract_audio
        fmt: audio format ("aac" or "mp3")

    Returns:
        transcript string or None if transcription fails

    Raises:
        ValueError: if audio_bytes is empty or invalid
        OpenAIError: if OpenAI API call fails
    """
    if not audio_bytes:
        error_msg = "audio_bytes cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not fmt or fmt not in ("aac", "mp3"):
        error_msg = f"Invalid audio format: {fmt}. Must be 'aac' or 'mp3'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Map extension properly
    ext = "aac" if fmt == "aac" else "mp3"

    try:
        # Wrap bytes as file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{ext}"

        logger.info(f"Starting transcription for {ext} audio ({len(audio_bytes)} bytes)")

        # Initialize client with API key from config
        client = OpenAI(api_key=settings.openai_api_key)

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

        result = transcript.text
        logger.info(f"Transcription completed successfully ({len(result)} chars)")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except OpenAIError as e:
        error_msg = f"OpenAI API error: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Unexpected error during transcription: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        raise
