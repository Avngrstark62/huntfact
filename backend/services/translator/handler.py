from typing import Optional
import logging
from logging_config import get_logger, log_event
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
    
    if not transcript_text:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No transcript_text found in payload",
            component="services.translator.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"translated_text": None, "error": "No transcript_text found in payload"}
    
    translated_text = await translate_text(transcript_text)
    
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
        return {"translated_text": None, "error": "Translation failed"}

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

    return {"translated_text": translated_text, "error": None}
