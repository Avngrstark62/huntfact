from typing import Optional
import base64
import logging
from logging_config import get_logger, log_event
from services.transcriber.assemblyai import transcribe_audio as assemblyai_transcribe_audio
from services.transcriber.openai import transcribe_audio as openai_transcribe_audio

logger = get_logger("services.transcriber.handler")


async def handle_transcribe(payload: dict | None = None) -> Optional[dict]:
    """
    Transcribe extracted audio from payload.

    Args:
        payload: dict containing audio_bytes_b64 and audio_format.

    Returns:
        dict containing transcript_text and error.
    """
    context = ((payload or {}).get("context") if isinstance(payload, dict) else {}) or {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Starting transcription",
        component="services.transcriber.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        step=context.get("step"),
    )
    
    audio_bytes_b64 = (payload or {}).get("audio_bytes_b64")
    audio_format = (payload or {}).get("audio_format")
    
    if not audio_bytes_b64:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No audio_bytes_b64 found in payload",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"transcript_text": None, "error": "No audio_bytes_b64 found in payload"}
    
    if not audio_format:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No audio_format found in payload",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"transcript_text": None, "error": "No audio_format found in payload"}
    
    # Decode audio from base64
    try:
        audio_bytes = base64.b64decode(audio_bytes_b64)
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Failed to decode audio bytes",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return {"transcript_text": None, "error": f"Failed to decode audio bytes: {str(e)}"}
    
    # Transcribe audio
    transcriber_service = payload.get("transcriber_service", "assemblyai")
    if transcriber_service == "assemblyai":
        result = await assemblyai_transcribe_audio(audio_bytes, audio_format)
    elif transcriber_service == "openai":
        result = await openai_transcribe_audio(audio_bytes, audio_format)
    else:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Unsupported transcriber service",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            transcriber_service=transcriber_service,
        )
        return {"transcript_text": None, "error": f"Unsupported transcriber service: {transcriber_service}"}
    
    if not result:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Transcription failed",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"transcript_text": None, "error": "Transcription failed"}

    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Transcription completed",
        component="services.transcriber.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"transcript_chars": len(result or "")},
    )

    return {"transcript_text": result, "error": None}
