from typing import Optional
import base64
import logging
from logging_config import get_logger, log_event
from s3_client import s3_client
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
    payload_data = payload or {}
    context = (payload_data.get("context") if isinstance(payload_data, dict) else {}) or {}
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
    
    audio_bytes_b64 = payload_data.get("audio_bytes_b64")
    audio_ref = payload_data.get("audio_ref")
    audio_format = payload_data.get("audio_format")

    if not audio_bytes_b64 and not isinstance(audio_ref, dict):
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No audio bytes reference found in task input",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"transcript_ref": None, "error": "No audio bytes reference found in payload"}
    
    if not audio_format:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No audio_format found in task input",
            component="services.transcriber.handler",
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        return {"transcript_ref": None, "error": "No audio_format found in payload"}

    audio_bytes: bytes | None = None
    if isinstance(audio_ref, dict):
        audio_key = audio_ref.get("key")
        if not isinstance(audio_key, str) or not audio_key.strip():
            return {"transcript_ref": None, "error": "Invalid audio_ref key"}
        try:
            audio_bytes = await s3_client.get_bytes(key=audio_key.strip())
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="task.failed",
                status="failed",
                message="Failed to download audio from S3",
                component="services.transcriber.handler",
                workflow_id=context.get("workflow_id"),
                hunt_id=context.get("hunt_id"),
                request_id=context.get("request_id"),
                task_id=context.get("task_id"),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            return {"transcript_ref": None, "error": f"Failed to download audio: {str(e)}"}
    else:
        # Backward compatibility for legacy payloads that still carry base64 audio inline.
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
            return {"transcript_ref": None, "error": f"Failed to decode audio bytes: {str(e)}"}
    
    # Transcribe audio
    transcriber_service = payload_data.get("transcriber_service", "assemblyai")
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
        return {"transcript_ref": None, "error": f"Unsupported transcriber service: {transcriber_service}"}
    
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
        return {"transcript_ref": None, "error": "Transcription failed"}

    workflow_id = str(context.get("workflow_id") or "")
    step = str(context.get("step") or "transcribe")
    task_id = str(context.get("task_id") or "")
    artifact_key = s3_client.build_artifact_key(
        workflow_id=workflow_id,
        step=step,
        task_id=task_id,
        artifact_name=f"transcript_{transcriber_service}",
        extension="json",
    )
    transcript_ref = await s3_client.put_json(
        key=artifact_key,
        payload={
            "transcript_text": result,
            "transcriber_service": transcriber_service,
            "audio_format": audio_format,
        },
        metadata={
            "workflow_id": workflow_id,
            "step": step,
            "task_id": task_id,
            "transcriber_service": transcriber_service,
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
        message="Transcription completed",
        component="services.transcriber.handler",
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
        task_id=context.get("task_id"),
        result_summary={"transcript_chars": len(result or "")},
    )

    return {"transcript_ref": transcript_ref, "error": None}
