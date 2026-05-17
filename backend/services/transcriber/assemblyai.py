"""
Audio transcription service using AssemblyAI REST API.
Handles audio bytes and returns only transcript text.
"""

import asyncio
from typing import Optional

import requests

from config import settings
from logging_config import get_logger

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
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not fmt or fmt not in ("aac", "mp3"):
        error_msg = f"Invalid audio format: {fmt}. Must be 'aac' or 'mp3'"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info(f"Starting transcription for {fmt} audio ({len(audio_bytes)} bytes)")
        
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
                logger.info("Transcription completed successfully")
                return result.get("text")

            elif status == "error":
                error_msg = f"AssemblyAI transcription failed: {result.get('error')}"
                logger.error(error_msg)
                raise Exception(error_msg)

            await asyncio.sleep(1)  # polling interval

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"AssemblyAI API error: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        raise
