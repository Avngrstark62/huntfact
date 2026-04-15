import asyncio
import signal
from typing import Optional
from logging_config import get_logger, setup_logging
from firebase_config import initialize_firebase
from rmq.constants import (
    EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE, EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS, SELECT_URLS, FETCH_PAGES, SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS, GENERATE_RESULT, SAVE_RESULT_TO_DB, NOTIFY
)
from rmq.consumer import start_consumer
from rmq.connection import rabbitmq
from rmq.schemas import TaskMessage
from rmq.publisher import publish_task
from rmq_redis import get_job_data, update_job_data
from services.audio_extractor.handler import handle_extract_audio
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

shutdown_event = asyncio.Event()


async def handle_task(msg: dict):
    """
    Main handler for incoming tasks from the queue.
    Fetches job state from Redis, routes to step-specific handler,
    updates state, and publishes next task.
    """
    job_id = None
    step = None
    try:
        job_id = msg.get("job_id")
        step = msg.get("step")
        payload = msg.get("payload", {})
        
        # Fetch job state from Redis
        job_state = get_job_data(job_id)
        if job_state is None:
            logger.error(f"[TASK HANDLER] Job state not found in Redis for job_id: {job_id}")
            return
        
        # Route to step-specific handler and get updated state and next task
        updated_state = None
        next_task = None
        
        if step == EXTRACT_AUDIO:
            updated_state, next_task = await handle_extract_audio(job_id, job_state)
        elif step == TRANSCRIBE:
            updated_state, next_task = await handle_transcribe(job_id, job_state)
        elif step == TRANSLATE:
            updated_state, next_task = await handle_translate(job_id, job_state)
        elif step == EXTRACT_QUESTIONS_QUERIES:
            updated_state, next_task = await handle_extract_questions_queries(job_id, job_state)
        elif step == FETCH_URLS:
            updated_state, next_task = await handle_fetch_urls(job_id, job_state)
        elif step == SELECT_URLS:
            updated_state, next_task = await handle_select_urls(job_id, job_state)
        elif step == FETCH_PAGES:
            updated_state, next_task = await handle_fetch_pages(job_id, job_state)
        elif step == SAVE_DATA_TO_RAG:
            updated_state, next_task = await handle_save_data_to_rag(job_id, job_state)
        elif step == ANSWER_QUESTIONS:
            updated_state, next_task = await handle_answer_questions(job_id, job_state)
        elif step == GENERATE_RESULT:
            updated_state, next_task = await handle_generate_result(job_id, job_state)
        elif step == SAVE_RESULT_TO_DB:
            updated_state, next_task = await handle_save_result_to_db(job_id, job_state)
        elif step == NOTIFY:
            updated_state, next_task = await handle_notify(job_id, job_state)
        else:
            logger.error(f"[TASK HANDLER] Unknown step: {step}")
            raise ValueError(f"Unknown step: {step}")
        
        # Update job state in Redis
        if updated_state is not None:
            update_job_data(job_id, updated_state)
        
        # Publish next task if provided
        if next_task is not None:
            await publish_task(next_task)
        
    except Exception as e:
        logger.error(f"[TASK HANDLER] Task failed - job_id: {job_id}, step: {step}, error: {str(e)}", exc_info=True)
        raise


async def main():
    setup_logging()
    initialize_firebase()
    logger.info("Starting worker...")
    
    loop = asyncio.get_event_loop()
    consumer_task = None
    
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()
    
    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)
    
    try:
        consumer_task = asyncio.create_task(start_consumer(handle_task))
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
