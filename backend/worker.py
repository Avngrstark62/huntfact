import asyncio
import signal
from typing import Optional
from logging_config import get_logger, setup_logging
from rmq.constants import EXTRACT_AUDIO, TRANSCRIBE, ANALYZE, NOTIFY
from rmq.consumer import start_consumer
from rmq.connection import rabbitmq
from rmq.schemas import TaskMessage
from rmq.publisher import publish_task
from redis import get_job_data, update_job_data
from services.audio_extractor.handler import handle_extract_audio

logger = get_logger("rmq.worker")

shutdown_event = asyncio.Event()


async def handle_task(msg: dict):
    """
    Main handler for incoming tasks from the queue.
    Fetches job state from Redis, routes to step-specific handler,
    updates state, and publishes next task.
    """
    try:
        job_id = msg.get("job_id")
        step = msg.get("step")
        payload = msg.get("payload", {})
        
        logger.info(f"Processing task - job_id: {job_id}, step: {step}")
        
        # Fetch job state from Redis
        job_state = get_job_data(job_id)
        if job_state is None:
            logger.error(f"Job state not found in Redis for job_id: {job_id}")
            return
        
        # Route to step-specific handler and get updated state and next task
        updated_state = None
        next_task = None
        
        if step == EXTRACT_AUDIO:
            updated_state, next_task = await handle_extract_audio(job_id, job_state)
        elif step == TRANSCRIBE:
            updated_state, next_task = await handle_transcribe(job_id, job_state)
        elif step == ANALYZE:
            updated_state, next_task = await handle_analyze(job_id, job_state)
        elif step == NOTIFY:
            updated_state, next_task = await handle_notify(job_id, job_state)
        else:
            logger.error(f"Unknown step: {step}")
            raise ValueError(f"Unknown step: {step}")
        
        # Update job state in Redis
        if updated_state is not None:
            update_job_data(job_id, updated_state)
            logger.info(f"Updated job state in Redis for job_id: {job_id}")
        
        # Publish next task if provided
        if next_task is not None:
            await publish_task(next_task)
            logger.info(f"Published next task: {next_task.step}")
        
        logger.info(f"Task completed - job_id: {job_id}, step: {step}")
        
    except Exception as e:
        logger.error(f"Task failed - job_id: {job_id}, step: {step}, error: {str(e)}", exc_info=True)
        raise


async def handle_transcribe(job_id: str, job_state: dict) -> tuple[dict, Optional[TaskMessage]]:
    """
    Transcribe the extracted audio.
    """
    logger.info(f"Transcribing audio for job {job_id}")
    # TODO: Implement transcription logic
    # - Read audio bytes from job_state
    # - Transcribe audio
    # - Update state with transcript
    # - Return updated state and next task
    return job_state, None


async def handle_analyze(job_id: str, job_state: dict) -> tuple[dict, Optional[TaskMessage]]:
    """
    Analyze the transcript for facts.
    """
    logger.info(f"Analyzing transcript for job {job_id}")
    # TODO: Implement analysis logic
    # - Read transcript from job_state
    # - Analyze for facts
    # - Update state with results
    # - Return updated state and next task
    return job_state, None


async def handle_notify(job_id: str, job_state: dict) -> tuple[dict, Optional[TaskMessage]]:
    """
    Notify user with results.
    """
    logger.info(f"Notifying user for job {job_id}")
    # TODO: Implement notification logic
    # - Send email/notification
    # - Update hunt status to completed
    # - Return updated state and no next task
    return job_state, None


async def main():
    setup_logging()
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
