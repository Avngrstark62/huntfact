"""
Audio transcription service using Azure Speech Batch Transcription API.
Handles audio bytes and returns only transcript text.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from typing import Optional

import requests

from config import settings
from logging_config import get_logger

logger = get_logger("services.transcriber.azure")


def _build_blob_url(container_sas_url: str, blob_name: str) -> str:
    parsed = urlsplit(container_sas_url)
    base_path = parsed.path.rstrip("/")
    blob_path = f"{base_path}/{blob_name}"
    return urlunsplit((parsed.scheme, parsed.netloc, blob_path, parsed.query, ""))


def _upload_audio_blob(audio_bytes: bytes, fmt: str) -> str:
    if not settings.transcription.azure_batch_input_container_sas_url:
        error_msg = "azure_batch_input_container_sas_url is not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)

    blob_name = f"transcription-input-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex}.{fmt}"
    blob_url = _build_blob_url(settings.transcription.azure_batch_input_container_sas_url, blob_name)

    content_type = "audio/mpeg" if fmt == "mp3" else "audio/aac"
    headers = {
        "x-ms-blob-type": "BlockBlob",
        "Content-Type": content_type,
    }

    response = requests.put(blob_url, headers=headers, data=audio_bytes)
    if response.status_code not in (201, 202):
        raise Exception(f"Azure blob upload failed: {response.status_code} {response.text}")

    return blob_url


def _delete_blob(blob_url: str) -> None:
    if not blob_url:
        return
    try:
        requests.delete(blob_url)
    except Exception as e:
        logger.warning(f"Failed to delete temporary blob: {type(e).__name__}: {str(e)}")


async def transcribe_audio(audio_bytes: bytes, fmt: str) -> Optional[str]:
    """
    Transcribe audio bytes using Azure Speech Batch Transcription API.

    Args:
        audio_bytes: raw bytes from extract_audio
        fmt: audio format ("aac" or "mp3")

    Returns:
        transcript text or None if transcription fails

    Raises:
        ValueError: if input settings/audio are invalid
        Exception: if Azure SDK call fails
    """
    if not audio_bytes:
        error_msg = "audio_bytes cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not fmt or fmt not in ("aac", "mp3"):
        error_msg = f"Invalid audio format: {fmt}. Must be 'aac' or 'mp3'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not settings.transcription.azure_speech_key:
        error_msg = "azure_speech_key is not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not settings.transcription.azure_speech_region:
        error_msg = "azure_speech_region is not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        logger.info(f"Starting Azure batch transcription for {fmt} audio ({len(audio_bytes)} bytes)")

        blob_url = _upload_audio_blob(audio_bytes, fmt)

        endpoint = (
            f"https://{settings.transcription.azure_speech_region}.api.cognitive.microsoft.com"
            f"/speechtotext/{settings.transcription.azure_speech_batch_api_version}/transcriptions"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.transcription.azure_speech_key,
            "Content-Type": "application/json",
        }
        payload = {
            "displayName": f"huntfact-transcription-{uuid.uuid4().hex[:8]}",
            "locale": settings.transcription.azure_speech_language,
            "contentUrls": [blob_url],
            "properties": {
                "diarizationEnabled": False,
                "wordLevelTimestampsEnabled": False,
                "punctuationMode": "DictatedAndAutomatic",
            },
        }

        create_response = requests.post(endpoint, headers=headers, json=payload)
        if create_response.status_code not in (200, 201, 202):
            raise Exception(
                f"Azure batch transcription request failed: {create_response.status_code} {create_response.text}"
            )

        transcription_url = create_response.headers.get("location")
        if not transcription_url:
            create_body = create_response.json()
            transcription_url = create_body.get("self")
        if not transcription_url:
            raise Exception("Azure batch transcription did not return a transcription URL")

        timeout_seconds = settings.transcription.azure_transcription_timeout_seconds
        poll_interval = settings.transcription.azure_batch_poll_interval_seconds
        elapsed_seconds = 0

        while True:
            status_response = requests.get(transcription_url, headers=headers)
            if status_response.status_code != 200:
                raise Exception(
                    f"Azure batch status request failed: {status_response.status_code} {status_response.text}"
                )

            status_body = status_response.json()
            status = status_body.get("status")

            if status == "Succeeded":
                files_url = status_body.get("links", {}).get("files")
                if not files_url:
                    raise Exception("Azure batch transcription result files URL is missing")

                files_response = requests.get(files_url, headers=headers)
                if files_response.status_code != 200:
                    raise Exception(
                        f"Azure batch files request failed: {files_response.status_code} {files_response.text}"
                    )

                files_body = files_response.json()
                values = files_body.get("values", [])
                transcription_file_url = None
                for item in values:
                    if item.get("kind") == "Transcription":
                        transcription_file_url = item.get("links", {}).get("contentUrl")
                        if transcription_file_url:
                            break

                if not transcription_file_url:
                    raise Exception("Azure batch transcription output file URL is missing")

                content_response = requests.get(transcription_file_url)
                if content_response.status_code != 200:
                    raise Exception(
                        f"Azure transcription content fetch failed: {content_response.status_code} {content_response.text}"
                    )

                content = content_response.json()
                phrases = content.get("combinedRecognizedPhrases", [])
                if phrases:
                    transcript_text = phrases[0].get("display", "").strip()
                else:
                    recognized_phrases = content.get("recognizedPhrases", [])
                    transcript_text = " ".join(
                        phrase.get("nBest", [{}])[0].get("display", "").strip()
                        for phrase in recognized_phrases
                    ).strip()

                logger.info("Azure batch transcription completed successfully")
                return transcript_text

            if status in ("Failed", "Cancelled"):
                details = status_body.get("properties", {}).get("error", {})
                error_message = details.get("message") or json.dumps(details) or "unknown error"
                raise Exception(f"Azure batch transcription failed: {error_message}")

            await asyncio.sleep(poll_interval)
            elapsed_seconds += poll_interval
            if elapsed_seconds >= timeout_seconds:
                raise TimeoutError(
                    f"Azure batch transcription timed out after {timeout_seconds} seconds"
                )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"Azure batch transcription error: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        raise
    finally:
        try:
            _delete_blob(locals().get("blob_url", ""))
        except Exception:
            pass
