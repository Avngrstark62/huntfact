import asyncio
import json
import signal

import aio_pika

from logging_config import get_logger, setup_logging
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
    finally:
        await reply_channel.close()


async def handle_task(msg: dict, raw_message: aio_pika.IncomingMessage):
    """Run one pipeline step. Sends RPC reply when the incoming message has reply_to."""
    step = None
    reply_to = _decode_reply_to(raw_message)

    try:
        step = msg.get("step")
        payload = msg.get("payload")

        if step == EXTRACT_AUDIO:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_extract_audio(payload)
            if result is None:
                raise RuntimeError("Audio extraction handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == TRANSCRIBE:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_transcribe(payload)
            if result is None:
                raise RuntimeError("Transcription handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == TRANSCRIPTION_CORRECT:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_correct_transcription(payload)
            if result is None:
                raise RuntimeError("transcription_corrector handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == TRANSLATE:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_translate(payload)
            if result is None:
                raise RuntimeError("Translation handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == EXTRACT_CLAIM_CLUSTERS:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_extract_claim_clusters(payload)
            if result is None:
                raise RuntimeError("Claim cluster extraction handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == URL_FETCHER:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_url_fetcher(payload)
            if result is None:
                raise RuntimeError("URL fetcher handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == WEB_SCRAPER:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_web_scraper(payload)
            if result is None:
                raise RuntimeError("Web scraper handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == RAG_STORAGE:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_rag_storage(payload)
            if result is None:
                raise RuntimeError("RAG storage handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == CLAIM_VERIFIER:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_claim_verifier(payload)
            if result is None:
                raise RuntimeError("Claim verifier handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == SAVE_RESULT_TO_DB:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_save_result_to_db(payload)
            if result is None:
                raise RuntimeError("save_result_to_db handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        if step == NOTIFY:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            result = await handle_notify(payload)
            if result is None:
                raise RuntimeError("notify handler returned no result")
            if result.get("error"):
                raise RuntimeError(result["error"])
            if reply_to:
                await _publish_task_reply(
                    raw_message,
                    reply_to,
                    {"status": "success", "step": step, "result": result},
                )
            return

        logger.error(f"[TASK HANDLER] No handler for step: {step}")
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
        logger.error(
            f"[TASK HANDLER] Task failed - step: {step}, error: {str(e)}",
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


async def main():
    setup_logging()
    try:
        initialize_firebase()
    except Exception as e:
        logger.error(
            "Firebase initialization failed at startup; worker will continue and notification tasks may fail: %s",
            str(e),
            exc_info=True,
        )
    logger.info("Starting worker...")

    loop = asyncio.get_event_loop()
    consumer_task = None

    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    try:
        consumer_task = asyncio.create_task(start_task_consumer(handle_task))
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Consumer was cancelled, shutting down...")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up resources...")
        try:
            await rabbitmq.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ: {str(e)}", exc_info=True)
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
