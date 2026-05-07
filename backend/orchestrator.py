import asyncio
import json
import signal

from logging_config import get_logger, setup_logging

from rmq.connection import rabbitmq
from rmq.consumer import start_workflow_consumer
from rmq.schemas import WorkflowMessage

logger = get_logger("workflow_orchestrator")


async def _add_three(workflow_id: str, state: dict) -> None:
    state["value"] = state["value"] + 3
    logger.info("workflow %s add_three -> %s", workflow_id, state["value"])


async def _double(workflow_id: str, state: dict) -> None:
    state["value"] = state["value"] * 2
    logger.info("workflow %s double -> %s", workflow_id, state["value"])


async def _minus_five(workflow_id: str, state: dict) -> None:
    state["value"] = state["value"] - 5
    logger.info("workflow %s minus_five -> %s", workflow_id, state["value"])


async def handle_workflow_message(msg: dict) -> None:
    try:
        workflow = WorkflowMessage.model_validate(msg)
        state = {"value": int(workflow.payload.get("start", 0))}

        logger.info("workflow %s start value=%s", workflow.workflow_id, state["value"])
        await _add_three(workflow.workflow_id, state)
        await _double(workflow.workflow_id, state)
        await _minus_five(workflow.workflow_id, state)
        logger.info("workflow %s finished final value=%s", workflow.workflow_id, state["value"])
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
