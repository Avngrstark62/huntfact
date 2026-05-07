import json
import aio_pika

from rmq.connection import rabbitmq
from config import settings
from rmq.schemas import TaskMessage, WorkflowMessage
from logging_config import get_logger

logger = get_logger("rmq.publisher")


async def publish_task(task: TaskMessage):
    channel = await rabbitmq.get_channel(settings.prefetch_count)

    try:
        await channel.declare_queue(
            settings.task_queue_name,
            durable=True,
            arguments={"x-max-priority": settings.max_priority},
        )

        message = aio_pika.Message(
            body=json.dumps(task.model_dump()).encode(),
            priority=task.priority,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.task_queue_name
        )
    finally:
        await channel.close()


async def publish_workflow(workflow: WorkflowMessage):
    channel = await rabbitmq.get_channel(settings.prefetch_count)

    try:
        await channel.declare_queue(
            settings.workflow_queue_name,
            durable=True,
        )

        message = aio_pika.Message(
            body=json.dumps(workflow.model_dump()).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.workflow_queue_name,
        )
    finally:
        await channel.close()
