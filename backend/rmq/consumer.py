import json
import asyncio
from logging_config import get_logger

from rmq.connection import rabbitmq
from config import settings

logger = get_logger("rmq.consumer")


async def start_consumer(handler):
    try:
        channel = await rabbitmq.get_channel(settings.prefetch_count)

        queue = await channel.declare_queue(
            settings.queue_name,
            durable=True,
            arguments={"x-max-priority": settings.max_priority}
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        msg = json.loads(message.body)
                        await handler(msg)
                    except Exception as e:
                        logger.error(f"[CONSUMER] Error processing message: {str(e)}", exc_info=True)
                        raise
    except Exception as e:
        logger.error(f"[CONSUMER] Consumer failed: {str(e)}", exc_info=True)
        raise
