from typing import Optional
import base64
import logging
from logging_config import get_logger, log_event, sanitize_url
from services.audio_extractor.audio_extractor import extract_audio

logger = get_logger("services.audio_extractor.handler")


async def handle_extract_audio(payload: dict | None = None) -> Optional[dict]:
    """
    Extract audio from URL given with payload.
    
    Args:
        payload: dict containing the cdn_link for audio extraction.
    
    Returns:
        dict containing base64 audio, format and error.
    """
    context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting audio extraction",
        component="services.audio_extractor.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        step=context.get("step"),
    )
    
    cdn_link = (payload or {}).get("cdn_link")
    
    if not cdn_link:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No cdn_link found in payload",
            component="services.audio_extractor.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return None

    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Extracting audio from CDN link",
        component="services.audio_extractor.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        cdn_link=sanitize_url(str(cdn_link)),
    )
    
    # Extract audio using the URL
    result = await extract_audio(cdn_link)
    
    # Update job state with audio extraction result
    audio = result.get("audio")
    audio_bytes_b64 = base64.b64encode(audio).decode("utf-8") if audio else None
    
    if result.get("error"):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Audio extraction failed",
            component="services.audio_extractor.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            error_message=result.get("error"),
        )
        return {
            "audio_bytes_b64": None,
            "audio_format": result.get("format"),
            "error": result.get("error"),
        }
    
    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Audio extraction completed",
        component="services.audio_extractor.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"audio_format": result.get("format"), "bytes_b64_len": len(audio_bytes_b64 or "")},
    )
    
    return {
        "audio_bytes_b64": audio_bytes_b64,
        "audio_format": result.get("format"),
        "error": None,
    }
