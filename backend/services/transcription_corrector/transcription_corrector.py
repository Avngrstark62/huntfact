from typing import List
import logging

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger, log_event

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
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No transcript candidates provided",
            component="services.transcription_corrector",
        )
        raise ValueError("No transcript candidates provided")

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Correcting transcription",
        component="services.transcription_corrector",
        provider="openai",
        operation="transcription_correct",
        result_summary={"candidate_count": len(normalized_transcripts)},
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
        model=settings.llm.reasoning_model,
        messages=messages,
        schema_model=CorrectedTranscriptionResponse,
    )

    corrected_transcript = (result.corrected_transcript or "").strip()
    if not corrected_transcript:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Reasoning model returned empty corrected transcript",
            component="services.transcription_corrector",
            provider="openai",
            operation="transcription_correct",
        )
        raise ValueError("Reasoning model returned an empty corrected transcript")

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.succeeded",
        status="succeeded",
        message="Transcription correction completed",
        component="services.transcription_corrector",
        provider="openai",
        operation="transcription_correct",
        result_summary={"output_chars": len(corrected_transcript)},
    )
    return corrected_transcript
