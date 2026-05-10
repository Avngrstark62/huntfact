from typing import Optional
from logging_config import get_logger
from services.translator.translator import translate_text

logger = get_logger("services.translator.handler")


async def handle_translate(payload: dict | None = None) -> Optional[dict]:
    """
    Translate transcript text to English.

    Args:
        payload: dict containing transcript_text.

    Returns:
        dict containing translated_text and error.
    """
    logger.info("Starting translation")
    
    transcript_text = (payload or {}).get("transcript_text")
    
    if not transcript_text:
        logger.error("No transcript_text found in payload")
        return {"translated_text": None, "error": "No transcript_text found in payload"}
    
    logger.info(f"Translating transcript text ({len(transcript_text)} chars)")
    
    translated_text = await translate_text(transcript_text)
    
    if not translated_text:
        logger.error("Translation failed")
        return {"translated_text": None, "error": "Translation failed"}
    
    logger.info("Translation completed")

    return {"translated_text": translated_text, "error": None}
