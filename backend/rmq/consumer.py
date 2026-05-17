import json

from logging_config import get_logger

from rmq.connection import rabbitmq
from config import settings

logger = get_logger("rmq.consumer")


async def start_task_consumer(handler):
    try:
        channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)

        queue = await channel.declare_queue(
            settings.rabbitmq.task_queue_name,
            durable=True,
            arguments={"x-max-priority": settings.rabbitmq.max_priority},
        )

        async with queue.iterator() as queue_iter:
            async for raw_message in queue_iter:
                async with raw_message.process():
                    try:
                        msg = json.loads(raw_message.body)
                        await handler(msg, raw_message)
                    except Exception as e:
                        logger.error(
                            f"[TASK_CONSUMER] Error processing message: {str(e)}",
                            exc_info=True,
                        )
                        raise
    except Exception as e:
        logger.error(f"[TASK_CONSUMER] Consumer failed: {str(e)}", exc_info=True)
        raise


async def start_workflow_consumer(handler):
    try:
        channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)

        queue = await channel.declare_queue(
            settings.rabbitmq.workflow_queue_name,
            durable=True,
        )

        async with queue.iterator() as queue_iter:
            async for raw_message in queue_iter:
                async with raw_message.process():
                    try:
                        msg = json.loads(raw_message.body)
                        await handler(msg)
                    except Exception as e:
                        logger.error(
                            f"[WORKFLOW_CONSUMER] Error processing message: {str(e)}",
                            exc_info=True,
                        )
                        raise
    except Exception as e:
        logger.error(f"[WORKFLOW_CONSUMER] Consumer failed: {str(e)}", exc_info=True)
        raise
