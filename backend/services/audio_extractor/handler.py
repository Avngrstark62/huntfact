from typing import Optional
import logging
from logging_config import get_logger, log_event, sanitize_url
from s3_client import s3_client
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
            message="No cdn_link found in task input",
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
    result = await extract_audio(cdn_link, hunt_id=context.get("hunt_id"))
    
    audio = result.get("audio")
    audio_format = result.get("format")
    
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
            "audio_ref": None,
            "audio_format": audio_format,
            "error": result.get("error"),
        }

    if not isinstance(audio, (bytes, bytearray)):
        return {
            "audio_ref": None,
            "audio_format": audio_format,
            "error": "Audio extraction returned invalid audio bytes",
        }

    workflow_id = str(context.get("workflow_id") or "")
    step = str(context.get("step") or "extract_audio")
    task_id = str(context.get("task_id") or "")
    artifact_key = s3_client.build_artifact_key(
        workflow_id=workflow_id,
        step=step,
        task_id=task_id,
        artifact_name="audio",
        extension=audio_format or "mp3",
    )
    audio_ref = await s3_client.put_bytes(
        key=artifact_key,
        body=bytes(audio),
        content_type="audio/mpeg",
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
        message="Audio extraction completed",
        component="services.audio_extractor.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"audio_format": audio_format, "audio_size_bytes": len(audio)},
    )
    
    return {
        "audio_ref": audio_ref,
        "audio_format": audio_format,
        "error": None,
    }
