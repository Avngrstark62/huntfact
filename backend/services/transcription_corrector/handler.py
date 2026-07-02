from typing import Optional
import logging

from logging_config import get_logger, log_event
from s3_client import s3_client
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
    transcript_refs = (payload or {}).get("transcript_refs")

    if not transcripts and isinstance(transcript_refs, list):
        transcripts = []
        for transcript_ref in transcript_refs:
            if not isinstance(transcript_ref, dict):
                continue
            transcript_key = transcript_ref.get("key")
            if not isinstance(transcript_key, str) or not transcript_key.strip():
                continue
            try:
                transcript_payload = await s3_client.get_json(key=transcript_key.strip())
            except Exception:
                continue
            transcript_text = transcript_payload.get("transcript_text") if isinstance(transcript_payload, dict) else None
            if isinstance(transcript_text, str) and transcript_text.strip():
                transcripts.append(transcript_text)

    if not transcripts:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No transcripts found in task input or transcript_refs",
            component="services.transcription_corrector.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"corrected_transcript_ref": None, "error": "No transcripts found in payload"}

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
        return {"corrected_transcript_ref": None, "error": f"Transcription correction failed: {str(e)}"}

    workflow_id = str(context.get("workflow_id") or "")
    step = str(context.get("step") or "transcription_correct")
    task_id = str(context.get("task_id") or "")
    artifact_key = s3_client.build_artifact_key(
        workflow_id=workflow_id,
        step=step,
        task_id=task_id,
        artifact_name="corrected_transcript",
        extension="json",
    )
    corrected_transcript_ref = await s3_client.put_json(
        key=artifact_key,
        payload={
            "corrected_transcript": corrected_transcript,
        },
        metadata={
            "workflow_id": workflow_id,
            "step": step,
            "task_id": task_id,
        },
        tags={
            "workflow_id": workflow_id,
            "step": step,
        },
    )

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
    return {"corrected_transcript_ref": corrected_transcript_ref, "error": None}
