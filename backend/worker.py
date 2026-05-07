import asyncio
import signal
from logging_config import get_logger, setup_logging
from firebase_config import initialize_firebase
from rmq.constants import (
    EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE, EXTRACT_QUESTIONS_QUERIES,
    FETCH_URLS, SELECT_URLS, FETCH_PAGES, SAVE_DATA_TO_RAG,
    ANSWER_QUESTIONS, GENERATE_RESULT, SAVE_RESULT_TO_DB, NOTIFY
)
from rmq.schemas import TaskMessage
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

class Pipeline:
    def __init__(self):
        self.x=1

    async def execute_step(self, step: str, job_id: str) -> bool:
        handlers = {
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
                NOTIFY: handle_notify
                }
        handler = handlers.get(step)
        if handler:
            return await handler(job_id)
        else:
            logger.error(f"Unknown step: {step} for job_id: {job_id}")
            return False

    def get_priority(self, step: str) -> int:
        priority_map = {
            EXTRACT_AUDIO: 1,
            TRANSCRIBE: 2,
            TRANSLATE: 3,
            EXTRACT_QUESTIONS_QUERIES: 4,
            FETCH_URLS: 5,
            SELECT_URLS: 6,
            FETCH_PAGES: 7,
            SAVE_DATA_TO_RAG: 8,
            ANSWER_QUESTIONS: 9,
            GENERATE_RESULT: 10,
            SAVE_RESULT_TO_DB: 11,
            NOTIFY: 12
        }
        return priority_map.get(step, 100)

    def get_next_step(self, current_step: str) -> str:
        step_sequence = [
            EXTRACT_AUDIO,
            TRANSCRIBE,
            TRANSLATE,
            NOTIFY
        ]
        try:
            current_index = step_sequence.index(current_step)
            if current_index < len(step_sequence) - 1:
                return step_sequence[current_index + 1]
        except ValueError:
            pass
        return None

    async def publish_next_task(self, step: str, job_id: str):
        next_step = self.get_next_step(step)
        if next_step:
            task_message = TaskMessage(
                job_id=job_id,
                step=next_step,
                priority=self.get_priority(next_step),
                payload={}
            )
            await publish_task(task_message)

pipeline = Pipeline()

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
        if not job_repository.job_exists(job_id):
            logger.error(f"[TASK HANDLER] Job state not found in Redis for job_id: {job_id}")
            return

        result = await pipeline.execute_step(step, job_id)
        if result:
            await pipeline.publish_next_task(step, job_id)
        else:
            logger.error(f"[TASK HANDLER] Step {step} failed for job_id: {job_id}, not publishing next task")
        
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
