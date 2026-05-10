import asyncio
import json
import signal

from logging_config import get_logger, setup_logging

from rmq.connection import rabbitmq
from rmq.consumer import start_workflow_consumer
from rmq.schemas import WorkflowMessage, TaskMessage
from rmq.publisher import publish_task_rpc
from rmq.constants import EXTRACT_AUDIO, TRANSCRIBE, TRANSLATE

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

        extract_response = await publish_task_rpc(
            TaskMessage(
                step=EXTRACT_AUDIO,
                priority=1,
                payload={"cdn_link": cdn_link},
            )
        )
        if extract_response.get("status") != "success":
            raise RuntimeError(f"EXTRACT_AUDIO failed: {extract_response}")
        extract_result = extract_response.get("result") or {}

        logger.info("EXTRACT_AUDIO completed")

        transcribe_response = await publish_task_rpc(
            TaskMessage(
                step=TRANSCRIBE,
                priority=2,
                payload={
                    "audio_bytes_b64": extract_result.get("audio_bytes_b64"),
                    "audio_format": extract_result.get("audio_format"),
                },
            )
        )
        if transcribe_response.get("status") != "success":
            raise RuntimeError(f"TRANSCRIBE failed: {transcribe_response}")
        transcribe_result = transcribe_response.get("result") or {}

        logger.info(f"TRANSCRIBE completed: {transcribe_result}")

        translate_response = await publish_task_rpc(
            TaskMessage(
                step=TRANSLATE,
                priority=3,
                payload={
                    "transcript_text": transcribe_result.get("transcript_text"),
                },
            )
        )
        if translate_response.get("status") != "success":
            raise RuntimeError(f"TRANSLATE failed: {translate_response}")
        translate_result = translate_response.get("result") or {}
        logger.info(f"TRANSLATE completed: {translate_result}")

        logger.info(
            "Workflow RPC chain completed: workflow_id=%s transcript_chars=%s translated_chars=%s",
            workflow_id,
            len(transcribe_result.get("transcript_text") or ""),
            len(translate_result.get("translated_text") or ""),
        )

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
