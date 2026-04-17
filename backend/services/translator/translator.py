from typing import List, Dict, Any
from logging_config import get_logger
from config import settings
from llm import llm
from pydantic import BaseModel

logger = get_logger("services.translator.translator")


class TranslationResponse(BaseModel):
    translated_texts: List[str]


async def translate_utterances(utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Translate utterances to English using OpenAI.
    
    Extracts text from utterances, translates them, and reconstructs the full utterance objects.
    
    Args:
        utterances: List of utterance dictionaries with speaker, text, start, end, confidence
    
    Returns:
        List of translated utterance dictionaries with same structure
    """
    logger.info(f"Translating {len(utterances)} utterances")
    
    if not utterances:
        logger.warning("No utterances to translate")
        return utterances
    
    texts = [u["text"] for u in utterances]
    
    prompt = f"""Your task is to translate the given texts into English while preserving the original meaning, tone, and intent as faithfully as possible.

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

STRUCTURE:
- Translate each input text independently.
- Do NOT merge or split texts.
- Preserve ordering and structure exactly.
- Return exactly {len(texts)} translated texts matching the input order.

AMBIGUITY HANDLING:
- Resolve ambiguity using surrounding context when possible.
- Avoid literal translations that break meaning.

Translate these texts to English:

{texts}"""
    
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
        
        translated_texts = result.translated_texts
        
        translated_utterances = []
        for original, translated_text in zip(utterances, translated_texts):
            utterance = original.copy()
            utterance["text"] = translated_text
            translated_utterances.append(utterance)
        
        logger.info(f"Successfully translated {len(translated_utterances)} utterances")
        
        return translated_utterances
    except Exception as e:
        logger.error(f"Failed to translate utterances: {str(e)}", exc_info=True)
        raise


