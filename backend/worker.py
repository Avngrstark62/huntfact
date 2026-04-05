import asyncio
import signal
from logging_config import get_logger, setup_logging
from rmq.constants import DOWNLOAD, TRANSCRIBE, ANALYZE, NOTIFY
from rmq.consumer import start_consumer
from rmq.connection import rabbitmq

logger = get_logger("rmq.worker")

shutdown_event = asyncio.Event()


async def handle_task(msg: dict):
    """
    Main handler for incoming tasks from the queue.
    Routes tasks to appropriate step handlers.
    """
    try:
        job_id = msg.get("job_id")
        step = msg.get("step")
        payload = msg.get("payload", {})
        
        logger.info(f"Processing task - job_id: {job_id}, step: {step}")
        
        if step == DOWNLOAD:
            await handle_download(job_id, payload)
        elif step == TRANSCRIBE:
            await handle_transcribe(job_id, payload)
        elif step == ANALYZE:
            await handle_analyze(job_id, payload)
        elif step == NOTIFY:
            await handle_notify(job_id, payload)
        else:
            logger.error(f"Unknown step: {step}")
            raise ValueError(f"Unknown step: {step}")
        
        logger.info(f"Task completed - job_id: {job_id}, step: {step}")
        
    except Exception as e:
        logger.error(f"Task failed - job_id: {job_id}, step: {step}, error: {str(e)}", exc_info=True)
        raise


async def handle_download(job_id: str, payload: dict):
    """
    Download video from CDN link.
    """
    hunt_id = payload.get("hunt_id")
    cdn_link = payload.get("cdn_link")
    
    logger.info(f"Downloading video for hunt {hunt_id} from {cdn_link}")
    # TODO: Implement video download logic
    # - Download from cdn_link
    # - Store locally
    # - Update hunt status
    pass


async def handle_transcribe(job_id: str, payload: dict):
    """
    Transcribe the downloaded video.
    """
    hunt_id = payload.get("hunt_id")
    
    logger.info(f"Transcribing video for hunt {hunt_id}")
    # TODO: Implement transcription logic
    # - Read video file
    # - Transcribe audio
    # - Save transcript
    pass


async def handle_analyze(job_id: str, payload: dict):
    """
    Analyze the transcript for facts.
    """
    hunt_id = payload.get("hunt_id")
    
    logger.info(f"Analyzing transcript for hunt {hunt_id}")
    # TODO: Implement analysis logic
    # - Read transcript
    # - Analyze for facts
    # - Generate results
    pass


async def handle_notify(job_id: str, payload: dict):
    """
    Notify user with results.
    """
    hunt_id = payload.get("hunt_id")
    result = payload.get("result")
    
    logger.info(f"Notifying user for hunt {hunt_id} with result: {result}")
    # TODO: Implement notification logic
    # - Send email/notification
    # - Update hunt status to completed
    pass


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
