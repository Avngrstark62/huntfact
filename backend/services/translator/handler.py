from typing import Optional
import logging
from logging_config import get_logger, log_event
from s3_client import s3_client
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
    context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting translation",
        component="services.translator.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        step=context.get("step"),
    )
    
    transcript_text = (payload or {}).get("transcript_text")
    corrected_transcript_ref = (payload or {}).get("corrected_transcript_ref")
    if not transcript_text and isinstance(corrected_transcript_ref, dict):
        corrected_key = corrected_transcript_ref.get("key")
        if isinstance(corrected_key, str) and corrected_key.strip():
            try:
                corrected_payload = await s3_client.get_json(key=corrected_key.strip())
                maybe_transcript = (
                    corrected_payload.get("corrected_transcript")
                    if isinstance(corrected_payload, dict)
                    else None
                )
                if isinstance(maybe_transcript, str) and maybe_transcript.strip():
                    transcript_text = maybe_transcript
            except Exception:
                transcript_text = None
    
    if not transcript_text:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No transcript_text found in task input or corrected_transcript_ref",
            component="services.translator.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"translated_text_ref": None, "error": "No transcript_text found in payload"}
    
    translated_text = await translate_text(
        transcript_text,
        hunt_id=context.get("hunt_id"),
    )
    
    if not translated_text:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Translation failed",
            component="services.translator.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"translated_text_ref": None, "error": "Translation failed"}

    workflow_id = str(context.get("workflow_id") or "")
    step = str(context.get("step") or "translate")
    task_id = str(context.get("task_id") or "")
    artifact_key = s3_client.build_artifact_key(
        workflow_id=workflow_id,
        step=step,
        task_id=task_id,
        artifact_name="translated_text",
        extension="json",
    )
    translated_text_ref = await s3_client.put_json(
        key=artifact_key,
        payload={"translated_text": translated_text},
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
        message="Translation completed",
        component="services.translator.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"translated_chars": len(translated_text or "")},
    )

    return {"translated_text_ref": translated_text_ref, "error": None}
