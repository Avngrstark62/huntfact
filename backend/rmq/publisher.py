import json
import aio_pika

from rmq.connection import rabbitmq
from config import settings
from rmq.schemas import TaskMessage


async def publish_task(task: TaskMessage):
    channel = await rabbitmq.get_channel(settings.prefetch_count)

    message = aio_pika.Message(
        body=json.dumps(task.model_dump()).encode(),
        priority=task.priority,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )

    await channel.default_exchange.publish(
        message,
        routing_key=settings.queue_name
    )
    
    await channel.close()
