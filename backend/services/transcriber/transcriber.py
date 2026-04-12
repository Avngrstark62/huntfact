"""
Audio transcription service using OpenAI's Whisper API.
Handles MP3 and other audio formats.
"""

from pathlib import Path
from typing import Optional

from openai import OpenAI

from config import settings
from logging_config import get_logger

logger = get_logger("services.transcriber.transcriber")


def transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Transcribe audio file to text using OpenAI's Whisper API.

    Args:
        audio_path: Path to the audio file (mp3, aac, wav, flac, ogg, m4a)

    Returns:
        Transcribed text or None if transcription fails

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If file format is not supported or file size exceeds limit
    """
    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
    if file_size_mb > settings.transcriber_max_audio_size_mb:
        raise ValueError(
            f"Audio file size ({file_size_mb:.2f}MB) exceeds max allowed "
            f"({settings.transcriber_max_audio_size_mb}MB)"
        )

    file_ext = audio_file.suffix.lstrip('.').lower()
    if file_ext not in settings.transcriber_supported_formats:
        raise ValueError(
            f"Unsupported audio format: {file_ext}. "
            f"Supported formats: {', '.join(settings.transcriber_supported_formats)}"
        )

    try:
        client = OpenAI(api_key=settings.openai_api_key)

        logger.info(f"Starting transcription for file: {audio_path}")

        with open(audio_file, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en"
            )

        transcribed_text = transcript.text
        logger.info(f"Transcription completed successfully: {audio_path}")

        return transcribed_text

    except FileNotFoundError as e:
        logger.error(f"File error during transcription: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error during transcription: {e}")
        raise
    except Exception as e:
        logger.error(f"Transcription failed for {audio_path}: {str(e)}")
        raise
