from typing import Optional
import base64
from logging_config import get_logger
from services.audio_extractor.audio_extractor import extract_audio

logger = get_logger("services.audio_extractor.handler")


async def handle_extract_audio(payload: dict | None = None) -> Optional[dict]:
    """
    Extract audio from URL given with payload.
    
    Args:
        payload: dict containing the cdn_link for audio extraction.
    
    Returns:
        dict containing base64 audio, format and error.
    """
    logger.info(f"Starting audio extraction")
    
    cdn_link = (payload or {}).get("cdn_link")
    
    if not cdn_link:
        logger.error(f"No cdn_link found in the payload")
        return None
    
    logger.info(f"Extracting audio from CDN link")
    
    # Extract audio using the URL
    result = await extract_audio(cdn_link)
    
    # Update job state with audio extraction result
    audio = result.get("audio")
    audio_bytes_b64 = base64.b64encode(audio).decode("utf-8") if audio else None
    
    if result.get("error"):
        logger.error(f"Audio extraction failed, error: {result.get('error')}")
        return {
            "audio_bytes_b64": None,
            "audio_format": result.get("format"),
            "error": result.get("error"),
        }
    
    logger.info(f"Audio extraction completed successfully")
    
    return {
        "audio_bytes_b64": audio_bytes_b64,
        "audio_format": result.get("format"),
        "error": None,
    }
