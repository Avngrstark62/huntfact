from typing import List

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger

logger = get_logger("services.transcription_corrector.transcription_corrector")

TRANSCRIPTION_CORRECTION_PROMPT = """You are given multiple ASR transcriptions of the same audio. Produce the single most likely correct transcription.

Rules:
- Compare all versions line-by-line and resolve conflicts using context, grammar, semantics, common speech patterns, and named entities.
- Prefer phrases that are contextually coherent over phonetically similar nonsense.
- Preserve the speaker’s wording, tone, slang, fillers, Hinglish, grammar mistakes, and code-switching. Do not rewrite professionally.
- Make only minimal corrections required to resolve obvious ASR mistakes.
- Use surrounding context to infer unclear words.
- Prefer consistent entity names, locations, dates, and repeated phrases across candidates.
- Output only the final merged transcription.
- Do not explain 
- Expect informal spoken language, fast speech, emotional emphasis, and mixed Hindi-English phrasing."""


class CorrectedTranscriptionResponse(BaseModel):
    corrected_transcript: str


def _normalize_transcripts(transcripts: List[str]) -> List[str]:
    normalized: List[str] = []
    for transcript in transcripts:
        cleaned_transcript = transcript.strip()
        if cleaned_transcript:
            normalized.append(cleaned_transcript)
    return normalized


async def correct_transcription(transcripts: List[str]) -> str:
    """
    Merge multiple transcript candidates into a single corrected transcript.

    Args:
        transcripts: Multiple transcript candidates of the same audio

    Returns:
        Corrected transcript text
    """
    normalized_transcripts = _normalize_transcripts(transcripts)

    if not normalized_transcripts:
        logger.error("No transcript candidates provided")
        raise ValueError("No transcript candidates provided")

    logger.info(
        "Correcting transcription from %s candidates",
        len(normalized_transcripts),
    )

    candidates_text = "\n\n".join(
        f"Candidate {idx}:\n{candidate}"
        for idx, candidate in enumerate(normalized_transcripts, start=1)
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"{TRANSCRIPTION_CORRECTION_PROMPT}\n\n"
                f"Transcription candidates:\n{candidates_text}\n\n"
                "Final merged transcription:"
            ),
        }
    ]

    result = await llm.call_with_schema(
        model=settings.models.reasoning_model,
        messages=messages,
        schema_model=CorrectedTranscriptionResponse,
    )

    corrected_transcript = (result.corrected_transcript or "").strip()
    if not corrected_transcript:
        logger.error("Reasoning model returned an empty corrected transcript")
        raise ValueError("Reasoning model returned an empty corrected transcript")

    logger.info("Transcription correction completed successfully")
    return corrected_transcript
