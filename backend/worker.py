import asyncio
import signal

from logging_config import get_logger, setup_logging
from firebase_config import initialize_firebase
from rmq.constants import (
    EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE, EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS, SELECT_URLS, FETCH_PAGES, SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS, GENERATE_RESULT, SAVE_RESULT_TO_DB, NOTIFY
)
from rmq.consumer import start_task_consumer
from rmq.connection import rabbitmq
from services.audio_extractor.audio_extractor import extract_audio
from services.transcriber.handler import handle_transcribe
from services.translator.handler import handle_translate
from services.extract_questions_queries.handler import handle_extract_questions_queries
from services.fetch_urls.handler import handle_fetch_urls
from services.select_urls.handler import handle_select_urls
from services.fetch_pages.handler import handle_fetch_pages
from services.save_data_to_rag.handler import handle_save_data_to_rag
from services.answer_questions.handler import handle_answer_questions
from services.generate_result.handler import handle_generate_result
from services.save_result_to_db.handler import handle_save_result_to_db
from services.notification_sender.handler import handle_notify

logger = get_logger("rmq.worker")


async def handle_task(msg: dict):
    """Run one pipeline step for a task message. Does not enqueue follow-up work."""
    step = None
    try:
        step = msg.get("step")
        payload = msg.get("payload")
        if step == EXTRACT_AUDIO:
            logger.info(f"[TASK HANDLER] Starting task - step: {step}")
            cdn_link = payload.get("cdn_link")
            audio_bytes = await extract_audio(cdn_link)
            logger.info(f"[TASK HANDLER] Extracted audio - step: {step}, audio_size: {len(audio_bytes)} bytes")
        else:
            logger.error(f"[TASK HANDLER] No handler for step: {step}")
    except Exception as e:
        logger.error(
            f"[TASK HANDLER] Task failed - step: {step}, error: {str(e)}",
            exc_info=True,
        )
        raise


async def main():
    setup_logging()
    initialize_firebase()
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
