import asyncio
import json
import signal

from logging_config import get_logger, setup_logging

from rmq.connection import rabbitmq
from rmq.consumer import start_workflow_consumer
from rmq.schemas import WorkflowMessage, TaskMessage
from rmq.publisher import publish_task
from rmq.constants import EXTRACT_AUDIO

logger = get_logger("workflow_orchestrator")

async def handle_workflow_message(msg: dict) -> None:
    try:
        workflow = WorkflowMessage.model_validate(msg)
        workflow_id = workflow.workflow_id
        payload = workflow.payload
        cdn_link = payload.get("cdn_link")
        logger.info(
            "Received workflow message: workflow_id=%s cdn_link=%s",
            workflow_id,
            cdn_link,
        )

        # audio extraction
        await publish_task(TaskMessage(
            step=EXTRACT_AUDIO,
            priority=1,
            payload={"cdn_link": cdn_link},
            ))

        logger.info("Published task for workflow_id=%s step=%s", workflow_id, EXTRACT_AUDIO)

    except Exception as e:
        logger.error(
            "Workflow execution failed: %s body=%s",
            e,
            json.dumps(msg)[:500],
            exc_info=True,
        )


async def main() -> None:
    setup_logging()
    logger.info("Starting workflow orchestrator...")

    loop = asyncio.get_event_loop()
    consumer_task = None

    def handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s, shutting down workflow orchestrator...", signum)
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()

    loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None)

    try:
        consumer_task = asyncio.create_task(
            start_workflow_consumer(handle_workflow_message)
        )
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Workflow consumer cancelled")
    finally:
        logger.info("Closing RabbitMQ connection...")
        try:
            await rabbitmq.close()
        except Exception as e:
            logger.error("Error closing RabbitMQ: %s", e, exc_info=True)
        logger.info("Workflow orchestrator stopped")


if __name__ == "__main__":
    asyncio.run(main())
