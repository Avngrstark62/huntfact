"""
Audio transcription service using OpenAI's Whisper API.
Handles audio bytes and returns transcribed text.
"""

import asyncio
import io
import logging
from typing import Optional

from openai import OpenAI, OpenAIError

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("services.transcriber.transcriber")


async def transcribe_audio(audio_bytes: bytes, fmt: str) -> Optional[str]:
    """
    Transcribe audio bytes using OpenAI Whisper API.

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
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message=error_msg,
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
        )
        raise ValueError(error_msg)

    if not fmt or fmt not in ("aac", "mp3"):
        error_msg = f"Invalid audio format: {fmt}. Must be 'aac' or 'mp3'"
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message=error_msg,
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
        )
        raise ValueError(error_msg)

    try:
        ext = "aac" if fmt == "aac" else "mp3"

        # Wrap bytes as file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{ext}"

        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.started",
            status="started",
            message="Starting OpenAI transcription",
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
            result_summary={"audio_bytes": len(audio_bytes), "format": ext},
        )

        # Initialize client with API key from config
        client = OpenAI(api_key=settings.openai.api_key)

        transcript = await asyncio.to_thread(
            client.audio.transcriptions.create,
            model="whisper-1",
            file=audio_file,
        )

        result = transcript.text
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="OpenAI transcription completed",
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
            result_summary={"transcript_chars": len(result)},
        )
        return result

    except ValueError as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="provider.request.failed",
            status="failed",
            message="OpenAI transcription validation error",
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise
    except OpenAIError as e:
        error_msg = f"OpenAI API error: {type(e).__name__}: {str(e)}"
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="OpenAI API error",
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise
    except Exception as e:
        error_msg = f"Unexpected error during transcription: {type(e).__name__}: {str(e)}"
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Unexpected OpenAI transcription error",
            component="services.transcriber.openai",
            provider="openai",
            operation="transcribe",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
