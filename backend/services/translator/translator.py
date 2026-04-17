from typing import List, Dict, Any
from logging_config import get_logger
from config import settings
from llm import llm
from pydantic import BaseModel

logger = get_logger("services.translator.translator")


class TranslatedUtterance(BaseModel):
    speaker: str
    text: str
    start: int
    end: int
    confidence: float


class TranslationResponse(BaseModel):
    utterances: List[TranslatedUtterance]


async def translate_utterances(utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Translate utterances to English using OpenAI.
    
    Preserves the structure of utterances while translating text to English.
    
    Args:
        utterances: List of utterance dictionaries with speaker, text, start, end, confidence
    
    Returns:
        List of translated utterance dictionaries with same structure
    """
    logger.info(f"Translating {len(utterances)} utterances")
    
    if not utterances:
        logger.warning("No utterances to translate")
        return utterances
    
    prompt = f"""Your task is to translate the given text into English while preserving the original meaning, tone, and intent as faithfully as possible.

CORE PRINCIPLE:
- Preserve meaning and intent exactly, while allowing minimal correction of obvious transcription errors.

CONTEXT:
- The input text comes from automatic speech transcription (ASR).
- It may contain minor errors such as misheard words, repeated words, or incorrect terms.

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

STRUCTURE:
- Translate each input segment independently.
- Do NOT merge or split segments.
- Preserve ordering and structure exactly.

AMBIGUITY HANDLING:
- Resolve ambiguity using surrounding context when possible.
- Avoid literal translations that break meaning.

Translate this to English:

{utterances}"""
    
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
            model=settings.cheap_model,
            messages=messages,
            schema_model=TranslationResponse,
        )
        
        translated_utterances = [u.model_dump() for u in result.utterances]
        
        logger.info(f"Successfully translated {len(translated_utterances)} utterances")
        
        return translated_utterances
    except Exception as e:
        logger.error(f"Failed to translate utterances: {str(e)}", exc_info=True)
        raise


