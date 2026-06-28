import asyncio
import json
import logging
import signal

import aio_pika

from logging_config import get_logger, log_event, setup_logging
from firebase_config import initialize_firebase
from rmq.constants import (
    EXTRACT_AUDIO,
    TRANSCRIBE,
    TRANSLATE,
    EXTRACT_CLAIM_CLUSTERS,
    URL_FETCHER,
    WEB_SCRAPER,
    RAG_STORAGE,
    CLAIM_VERIFIER,
    SAVE_RESULT_TO_DB,
    NOTIFY,
)
from rmq.consumer import start_task_consumer
from rmq.connection import rabbitmq
from rmq.schemas import validate_task_step_result
from services.audio_extractor.handler import handle_extract_audio
from services.transcriber.handler import handle_transcribe
from services.translator.handler import handle_translate
from services.claim_extractor.handler import handle_extract_claim_clusters
from services.url_fetcher.handler import handle_url_fetcher
from services.web_scraper.handler import handle_web_scraper
from services.rag_storage.handler import handle_rag_storage
from services.claim_verifier.handler import handle_claim_verifier
from services.save_result_to_db.handler import handle_save_result_to_db
from services.notification_sender.handler import handle_notify
from services.transcription_corrector.handler import handle_correct_transcription

logger = get_logger("rmq.worker")
TRANSCRIPTION_CORRECT = "TRANSCRIPTION_CORRECT"


def _decode_reply_to(raw_message: aio_pika.IncomingMessage) -> str | None:
    rto = raw_message.reply_to
    if not rto:
        return None
    if isinstance(rto, bytes):
        return rto.decode()
    return str(rto)


def _decode_correlation_id(raw_message: aio_pika.IncomingMessage) -> str | None:
    cid = raw_message.correlation_id
    if cid is None:
        return None
    if isinstance(cid, bytes):
        return cid.decode()
    return str(cid)


async def _publish_task_reply(
    raw_message: aio_pika.IncomingMessage,
    reply_to: str,
    body: dict,
) -> None:
    cid = _decode_correlation_id(raw_message)
    msg_kwargs: dict = {
        "body": json.dumps(body, default=str).encode(),
    }
    if cid is not None:
        msg_kwargs["correlation_id"] = cid
    reply_channel = await rabbitmq.get_channel()
    try:
        await reply_channel.default_exchange.publish(
            aio_pika.Message(**msg_kwargs),
            routing_key=reply_to,
        )
        log_event(
            logger,
            level=logging.INFO,
            event="rmq.rpc.reply.received",
            status="succeeded",
            message="Published RPC reply",
            component="worker",
            correlation_id=cid,
            reply_to=reply_to,
            routing_key=raw_message.routing_key,
        )
    except Exception as exc:
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.rpc.reply.failed",
            status="failed",
            message="Failed to publish RPC reply",
            component="worker",
            correlation_id=cid,
            reply_to=reply_to,
            routing_key=raw_message.routing_key,
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )
        raise
    finally:
        await reply_channel.close()


def _validated_step_result(step: str, result: dict) -> dict:
    try:
        return validate_task_step_result(step, result)
    except Exception as e:
        raise RuntimeError(f"Invalid success payload for step {step}: {str(e)}") from e


async def handle_task(msg: dict, raw_message: aio_pika.IncomingMessage):
    """Run one pipeline step. Sends RPC reply when the incoming message has reply_to."""
    step = None
    reply_to = _decode_reply_to(raw_message)
    task_status = "failed"
    payload = msg.get("payload") if isinstance(msg, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    context = payload.get("context")
    context = context if isinstance(context, dict) else {}

    try:
        step = msg.get("step")
        log_event(
            logger,
            level=logging.INFO,
            event="task.started",
            status="started",
            message="Starting worker task",
            component="worker",
            step=step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            correlation_id=_decode_correlation_id(raw_message),
            reply_to=reply_to,
            rpc_mode=bool(reply_to),
        )

        if step == EXTRACT_AUDIO:
            result = await handle_extract_audio(payload)
            if result is None:
                raise RuntimeError("Audio extraction handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == TRANSCRIBE:
            result = await handle_transcribe(payload)
            if result is None:
                raise RuntimeError("Transcription handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == TRANSCRIPTION_CORRECT:
            result = await handle_correct_transcription(payload)
            if result is None:
                raise RuntimeError("transcription_corrector handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == TRANSLATE:
            result = await handle_translate(payload)
            if result is None:
                raise RuntimeError("Translation handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == EXTRACT_CLAIM_CLUSTERS:
            result = await handle_extract_claim_clusters(payload)
            if result is None:
                raise RuntimeError("Claim cluster extraction handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == URL_FETCHER:
            result = await handle_url_fetcher(payload)
            if result is None:
                raise RuntimeError("URL fetcher handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == WEB_SCRAPER:
            result = await handle_web_scraper(payload)
            if result is None:
                raise RuntimeError("Web scraper handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == RAG_STORAGE:
            result = await handle_rag_storage(payload)
            if result is None:
                raise RuntimeError("RAG storage handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == CLAIM_VERIFIER:
            result = await handle_claim_verifier(payload)
            if result is None:
                raise RuntimeError("Claim verifier handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == SAVE_RESULT_TO_DB:
            result = await handle_save_result_to_db(payload)
            if result is None:
                raise RuntimeError("save_result_to_db handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        if step == NOTIFY:
            result = await handle_notify(payload)
            if result is None:
                raise RuntimeError("notify handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            validated_result = _validated_step_result(step, result)
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": validated_result},
                )
            task_status = "succeeded"
            return

        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="No handler for step",
            component="worker",
            step=step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
        )
        if reply_to:
            await _publish_task_reply(
                raw_message,
                reply_to,
                {
                    "status": "error",
                    "step": step,
                    "error": f"No handler for step: {step}",
                },
            )
        return

    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Worker task failed",
            component="worker",
            step=step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            task_id=context.get("task_id"),
            correlation_id=_decode_correlation_id(raw_message),
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        if reply_to:
            await _publish_task_reply(
                raw_message,
                reply_to,
                {"status": "error", "step": step, "error": str(e)},
            )
            return
        raise
    finally:
        if task_status == "succeeded":
            log_event(
                logger,
                level=logging.INFO,
                event="task.succeeded",
                status="succeeded",
                message="Worker task completed",
                component="worker",
                step=step,
                workflow_id=context.get("workflow_id"),
                hunt_id=context.get("hunt_id"),
                request_id=context.get("request_id"),
                task_id=context.get("task_id"),
                correlation_id=_decode_correlation_id(raw_message),
            )


async def main():
    setup_logging()
    try:
        initialize_firebase()
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="app.lifecycle.failed",
            status="failed",
            message="Firebase initialization failed at worker startup",
            component="worker",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
    log_event(
        logger,
        level=logging.INFO,
        event="app.lifecycle.started",
        status="started",
        message="Starting worker",
        component="worker",
    )

    loop = asyncio.get_event_loop()
    consumer_task = None

    def handle_shutdown(signum, frame):
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.cancelled",
            status="cancelled",
            message="Worker received shutdown signal",
            component="worker",
            signal=signum,
        )
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    try:
        consumer_task = asyncio.create_task(start_task_consumer(handle_task))
        await consumer_task
    except asyncio.CancelledError:
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.cancelled",
            status="cancelled",
            message="Worker consumer cancelled",
            component="worker",
        )
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="app.lifecycle.failed",
            status="failed",
            message="Worker error",
            component="worker",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
    finally:
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.cancelled",
            status="cancelled",
            message="Cleaning up worker resources",
            component="worker",
        )
        try:
            await rabbitmq.close()
            log_event(
                logger,
                level=logging.INFO,
                event="app.lifecycle.cancelled",
                status="cancelled",
                message="Worker RabbitMQ connection closed",
                component="worker",
            )
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="app.lifecycle.failed",
                status="failed",
                message="Error closing worker RabbitMQ",
                component="worker",
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
        log_event(
            logger,
            level=logging.INFO,
            event="app.lifecycle.succeeded",
            status="cancelled",
            message="Worker shutdown complete",
            component="worker",
        )


if __name__ == "__main__":
    asyncio.run(main())
