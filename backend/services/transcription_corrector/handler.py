from typing import Optional

from logging_config import get_logger
from services.transcription_corrector.transcription_corrector import (
    correct_transcription,
)

logger = get_logger("services.transcription_corrector.handler")


async def handle_correct_transcription(payload: dict | None = None) -> Optional[dict]:
    """
    Correct transcription by merging multiple transcript candidates.

    Args:
        payload: Dict containing transcripts.

    Returns:
        Dict with corrected_transcript and error.
    """
    logger.info("Starting transcription correction")

    transcripts = (payload or {}).get("transcripts")

    if not transcripts:
        logger.error("No transcripts found in payload")
        return {
            "corrected_transcript": None,
            "error": "No transcripts found in payload",
        }

    try:
        corrected_transcript = await correct_transcription(transcripts)
    except Exception as e:
        logger.error(f"Transcription correction failed: {str(e)}", exc_info=True)
        return {
            "corrected_transcript": None,
            "error": f"Transcription correction failed: {str(e)}",
        }

    logger.info("Transcription correction completed")
    return {"corrected_transcript": corrected_transcript, "error": None}
