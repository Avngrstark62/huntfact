from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from pydantic import BaseModel
from config import settings
from typing import List, Optional
from logging_config import get_logger

logger = get_logger("agents.translation")

class TranslatedUtterance(BaseModel):
    speaker: str
    text: str
    start: int
    end: int
    confidence: float

class TranslationResult(BaseModel):
    utterances: List[TranslatedUtterance]
    language_code: str
    confidence: float
    audio_duration: int

class TranslatedUtterances(BaseModel):
    utterances: List[TranslatedUtterance]

_agent: Optional[Agent] = None

def _create_model():
    """Create model based on configured provider"""
    provider = settings.claim_extraction_model_provider.lower()
    model_name = settings.claim_extraction_model_name
    
    if provider == "openai":
        return OpenAIChat(
            id=model_name,
            api_key=settings.openai_api_key,
            temperature=0.1
        )
    elif provider == "google":
        return Gemini(
            id=model_name,
            api_key=settings.google_api_key,
            temperature=0.1
        )
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

def get_agent() -> Agent:
    global _agent
    if _agent is None:
        logger.info(f"Initializing Translation Agent with {settings.claim_extraction_model_provider} provider")
        _agent = Agent(
            name="TranslationAgent",
            model=_create_model(),
            description="You are a precise translation engine.",
            instructions=[
    "Your task is to translate the given text into English while preserving the original meaning, tone, and intent as faithfully as possible.",
    "",
    "CORE PRINCIPLE:",
    "- Preserve meaning and intent exactly, while allowing minimal correction of obvious transcription errors.",
    "",
    "CONTEXT:",
    "- The input text comes from automatic speech transcription (ASR).",
    "- It may contain minor errors such as misheard words, repeated words, or incorrect terms.",
    "",
    "GUIDELINES:",
    "- Do NOT paraphrase or summarize.",
    "- Do NOT omit or add information.",
    "- Preserve tone (e.g., sarcasm, criticism, aggression, informality).",
    "- Keep strong or informal words with equivalent intensity.",
    "",
    "ERROR HANDLING (IMPORTANT):",
    "- If a word or phrase is clearly incorrect due to transcription error, infer the most likely intended meaning using context.",
    "- Correct only obvious errors.",
    "- Do NOT over-correct or reinterpret meaning.",
    "- When unsure, prefer the closest reasonable meaning rather than a literal but incorrect translation.",
    "",
    "STRUCTURE:",
    "- Translate each input segment independently.",
    "- Do NOT merge or split segments.",
    "- Preserve ordering and structure exactly.",
    "",
    "AMBIGUITY HANDLING:",
    "- Resolve ambiguity using surrounding context when possible.",
    "- Avoid literal translations that break meaning.",
    "",
    "OUTPUT FORMAT:",
    "- Return ONLY the translated text.",
    "- No explanations.",
    "- No extra formatting.",
    "",
    "Your goal is faithful meaning preservation, not literal word-for-word translation."
],
            output_schema=TranslatedUtterances,
        )
    return _agent

async def translate_text(transcription_data: dict) -> TranslationResult:
    logger.info("Starting translation")
    
    if not transcription_data or not transcription_data.get("utterances"):
        logger.error("No utterances provided")
        return TranslationResult(
            utterances=[],
            language_code=transcription_data.get("language_code", "unknown"),
            confidence=transcription_data.get("confidence", 0.0),
            audio_duration=transcription_data.get("audio_duration", 0)
        )
    
    # Extract data to pass only utterances to LLM
    utterances = transcription_data.get("utterances", [])
    language_code = transcription_data.get("language_code", "unknown")
    confidence = transcription_data.get("confidence", 0.0)
    audio_duration = transcription_data.get("audio_duration", 0)
    
    agent = get_agent()
    response = await agent.arun(f"Translate this transcription data to English:\n\n{str(utterances)}")
    
    result = response.content
    
    # Return with original confidence and audio_duration
    return TranslationResult(
        utterances=result.utterances,
        language_code=language_code,
        confidence=confidence,
        audio_duration=audio_duration
    )
