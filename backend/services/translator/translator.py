from typing import Optional
from logging_config import get_logger
from config import settings
from llm import llm
from pydantic import BaseModel

logger = get_logger("services.translator.translator")


class TranslationResponse(BaseModel):
    translated_text: str


async def translate_text(text: str) -> str:
    """
    Translate text to English using OpenAI.

    Args:
        text: Input transcript text

    Returns:
        Translated English text
    """
    if not text:
        logger.warning("No text to translate")
        return text

    logger.info(f"Translating text to English ({len(text)} chars)")

    prompt = f"""Your task is to translate the given text into English while preserving the original meaning, tone, and intent as faithfully as possible.

CORE PRINCIPLE:
- Preserve meaning and intent exactly, while allowing minimal correction of obvious transcription errors.

CONTEXT:
- The input texts come from automatic speech transcription (ASR).
- They may contain minor errors such as misheard words, repeated words, or incorrect terms.

GUIDELINES:
- Do NOT paraphrase or summarize.
- Do NOT omit or add information.
- Preserve tone (e.g., sarcasm, criticism, aggression, informality).
- Keep strong or informal words with equivalent intensity.

ERROR HANDLING (IMPORTANT):
- If a word or phrase is clearly incorrect due to transcription error, infer the most likely intended meaning using context.
- Correct only obvious errors.
- Do NOT over-correct or reinterpret meaning.
- When unsure, prefer the closest reasonable meaning rather than a literal but incorrect translation.

AMBIGUITY HANDLING:
- Resolve ambiguity using surrounding context when possible.
- Avoid literal translations that break meaning.

Translate this text to English and return only the translated text:

{text}"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a precise translation engine."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    try:
        result = await llm.call_with_schema(
            model=settings.models.cheap_model,
            messages=messages,
            schema_model=TranslationResponse,
        )

        translated_text: Optional[str] = result.translated_text
        final_text = (translated_text or "").strip()
        logger.info(f"Successfully translated text ({len(final_text)} chars)")
        return final_text
    except Exception as e:
        logger.error(f"Failed to translate text: {str(e)}", exc_info=True)
        raise
