"""
Audio transcription service using AssemblyAI REST API.
Handles audio bytes and returns only transcript text.
"""

import asyncio
import logging
from typing import Optional

import requests

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("services.transcriber.transcriber")


ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"


async def transcribe_audio(audio_bytes: bytes, fmt: str) -> Optional[str]:
    """
    Transcribe audio bytes using AssemblyAI REST API.
    
    Args:
        audio_bytes: raw bytes from extract_audio
        fmt: audio format ("aac" or "mp3")
    
    Returns:
        transcript text or None if transcription fails
    
    Raises:
        ValueError: if audio_bytes is empty or invalid
        Exception: if AssemblyAI API call fails
    """
    if not audio_bytes:
        error_msg = "audio_bytes cannot be empty"
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message=error_msg,
            component="services.transcriber.assemblyai",
            provider="assemblyai",
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
            component="services.transcriber.assemblyai",
            provider="assemblyai",
            operation="transcribe",
        )
        raise ValueError(error_msg)
    
    try:
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.started",
            status="started",
            message="Starting AssemblyAI transcription",
            component="services.transcriber.assemblyai",
            provider="assemblyai",
            operation="transcribe",
            result_summary={"audio_bytes": len(audio_bytes), "format": fmt},
        )
        
        headers = {
            "authorization": settings.assemblyai.api_key,
            "content-type": "application/json"
        }

        # ------------------------
        # STEP 1: Upload audio
        # ------------------------
        upload_headers = {
            "authorization": settings.assemblyai.api_key
        }

        upload_response = requests.post(
            ASSEMBLYAI_UPLOAD_URL,
            headers=upload_headers,
            data=audio_bytes
        )

        if upload_response.status_code != 200:
            raise Exception(f"Upload failed: {upload_response.text}")

        audio_url = upload_response.json()["upload_url"]

        # ------------------------
        # STEP 2: Request transcript
        # ------------------------
        transcript_request = {
            "audio_url": audio_url,
            "speech_models": ["universal-2"]            # 🔑 correct field
        }

        response = requests.post(
            ASSEMBLYAI_TRANSCRIPT_URL,
            json=transcript_request,
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Transcript request failed: {response.text}")

        transcript_id = response.json()["id"]

        # ------------------------
        # STEP 3: Poll for result
        # ------------------------
        polling_endpoint = f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}"

        while True:
            polling_response = requests.get(polling_endpoint, headers=headers)
            result = polling_response.json()

            status = result.get("status")

            if status == "completed":
                log_event(
                    logger,
                    level=logging.INFO,
                    event="provider.request.succeeded",
                    status="succeeded",
                    message="AssemblyAI transcription completed",
                    component="services.transcriber.assemblyai",
                    provider="assemblyai",
                    operation="transcribe",
                )
                return result.get("text")

            elif status == "error":
                error_msg = f"AssemblyAI transcription failed: {result.get('error')}"
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="provider.request.failed",
                    status="failed",
                    message="AssemblyAI transcription failed",
                    component="services.transcriber.assemblyai",
                    provider="assemblyai",
                    operation="transcribe",
                    error_message=error_msg,
                )
                raise Exception(error_msg)

            await asyncio.sleep(1)  # polling interval

    except ValueError as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="provider.request.failed",
            status="failed",
            message="AssemblyAI transcription validation error",
            component="services.transcriber.assemblyai",
            provider="assemblyai",
            operation="transcribe",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise
    except Exception as e:
        error_msg = f"AssemblyAI API error: {type(e).__name__}: {str(e)}"
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="AssemblyAI transcription failed",
            component="services.transcriber.assemblyai",
            provider="assemblyai",
            operation="transcribe",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
