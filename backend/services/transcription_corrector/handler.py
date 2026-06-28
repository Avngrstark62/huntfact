from typing import Optional
import logging

from logging_config import get_logger, log_event
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
    context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting transcription correction",
        component="services.transcription_corrector.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        step=context.get("step"),
    )

    transcripts = (payload or {}).get("transcripts")

    if not transcripts:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No transcripts found in payload",
            component="services.transcription_corrector.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {
            "corrected_transcript": None,
            "error": "No transcripts found in payload",
        }

    try:
        corrected_transcript = await correct_transcription(transcripts)
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Transcription correction failed",
            component="services.transcription_corrector.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {
            "corrected_transcript": None,
            "error": f"Transcription correction failed: {str(e)}",
        }

    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Transcription correction completed",
        component="services.transcription_corrector.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"corrected_chars": len(corrected_transcript or "")},
    )
    return {"corrected_transcript": corrected_transcript, "error": None}
