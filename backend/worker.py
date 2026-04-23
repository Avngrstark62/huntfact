import asyncio
import signal
from logging_config import get_logger, setup_logging
from firebase_config import initialize_firebase
from rmq.constants import (
    EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE, EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS, SELECT_URLS, FETCH_PAGES, SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS, GENERATE_RESULT, SAVE_RESULT_TO_DB, NOTIFY
)
from rmq.consumer import start_consumer
from rmq.connection import rabbitmq
from rmq.publisher import publish_task
from rmq_redis import job_repository
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

HANDLERS = {
    EXTRACT_AUDIO: handle_extract_audio,
    TRANSCRIBE: handle_transcribe,
    TRANSLATE: handle_translate,
    EXTRACT_QUESTIONS_QUERIES: handle_extract_questions_queries,
    FETCH_URLS: handle_fetch_urls,
    SELECT_URLS: handle_select_urls,
    FETCH_PAGES: handle_fetch_pages,
    SAVE_DATA_TO_RAG: handle_save_data_to_rag,
    ANSWER_QUESTIONS: handle_answer_questions,
    GENERATE_RESULT: handle_generate_result,
    SAVE_RESULT_TO_DB: handle_save_result_to_db,
    NOTIFY: handle_notify,
}

EXPECTED_NEXT_STEP = {
    EXTRACT_AUDIO: TRANSCRIBE,
    TRANSCRIBE: TRANSLATE,
    TRANSLATE: EXTRACT_QUESTIONS_QUERIES,
    EXTRACT_QUESTIONS_QUERIES: FETCH_URLS,
    FETCH_URLS: SELECT_URLS,
    SELECT_URLS: FETCH_PAGES,
    FETCH_PAGES: SAVE_DATA_TO_RAG,
    SAVE_DATA_TO_RAG: None,
    ANSWER_QUESTIONS: None,
    GENERATE_RESULT: SAVE_RESULT_TO_DB,
    SAVE_RESULT_TO_DB: NOTIFY,
    NOTIFY: None,
}


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
        payload = msg.get("payload")
        if not job_repository.job_exists(job_id):
            logger.error(f"[TASK HANDLER] Job state not found in Redis for job_id: {job_id}")
            return

        handler = HANDLERS.get(step)
        expected_next_step = EXPECTED_NEXT_STEP.get(step)
        if handler is None:
            logger.error(f"[TASK HANDLER] Unknown step: {step}")
            raise ValueError(f"Unknown step: {step}")

        if job_repository.get_step_state(job_id, step) == "done":
            logger.info(f"[TASK HANDLER] Step already done, skipping - job_id: {job_id}, step: {step}")
            return

        job_repository.set_step_state(job_id, step, "running")
        job_repository.set_job_status(
            job_id,
            "running",
            current_step=step,
            error_code=None,
            error_message=None,
        )

        next_task = await handler(job_id, payload)

        if next_task is None and expected_next_step is not None:
            job_repository.set_step_state(job_id, step, "failed")
            job_repository.set_job_status(
                job_id,
                "failed",
                current_step=step,
                error_code="STEP_FAILED",
                error_message=f"Step {step} failed to produce next task",
            )
            return

        answer_fanin_complete = step == ANSWER_QUESTIONS and next_task is not None
        if step != ANSWER_QUESTIONS:
            job_repository.set_step_state(job_id, step, "done")

        if step == SAVE_DATA_TO_RAG and next_task is None:
            job_repository.set_step_state(job_id, ANSWER_QUESTIONS, "running")

        if step == NOTIFY:
            job_repository.set_job_status(
                job_id,
                "completed",
                current_step=step,
                error_code=None,
                error_message=None,
            )
        else:
            if step == SAVE_DATA_TO_RAG and next_task is None:
                current_step = ANSWER_QUESTIONS
            elif step == ANSWER_QUESTIONS:
                current_step = next_task.step if next_task is not None else ANSWER_QUESTIONS
            else:
                current_step = next_task.step if next_task is not None else step
            job_repository.set_job_status(
                job_id,
                "running",
                current_step=current_step,
                error_code=None,
                error_message=None,
            )

        if next_task is not None:
            await publish_task(next_task)
        if answer_fanin_complete:
            job_repository.set_step_state(job_id, step, "done")
        
    except Exception as e:
        if job_id and step:
            try:
                job_repository.set_step_state(job_id, step, "failed")
                job_repository.set_job_status(
                    job_id,
                    "failed",
                    current_step=step,
                    error_code=type(e).__name__,
                    error_message=str(e),
                )
            except Exception:
                logger.error("[TASK HANDLER] Failed to persist worker error state", exc_info=True)
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
