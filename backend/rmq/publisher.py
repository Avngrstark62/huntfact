import asyncio
import json
import uuid

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


async def publish_task_rpc(task: TaskMessage, *, timeout: float | None = None) -> dict:
    """
    Publish a task and await the worker reply via RabbitMQ direct reply-to (RPC-style).

    Returns the decoded JSON body from the worker response.
    Raises asyncio.TimeoutError if timeout is set and no reply arrives in time.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    correlation_id = str(uuid.uuid4())

    async def on_response(message: aio_pika.IncomingMessage):
        try:
            if str(message.correlation_id or "") != correlation_id:
                return
            body = json.loads(message.body.decode())
            if not future.done():
                future.set_result(body)
        except Exception as e:
            if not future.done():
                future.set_exception(e)

    channel = await rabbitmq.get_channel(settings.prefetch_count)

    try:
        await channel.set_qos(prefetch_count=1)

        reply_queue = await channel.declare_queue(
            "amq.rabbitmq.reply-to",
            passive=True,
        )

        await reply_queue.consume(on_response, no_ack=True)

        await channel.declare_queue(
            settings.task_queue_name,
            durable=True,
            arguments={"x-max-priority": settings.max_priority},
        )

        message = aio_pika.Message(
            body=json.dumps(task.model_dump()).encode(),
            priority=task.priority,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=correlation_id,
            reply_to="amq.rabbitmq.reply-to",
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.task_queue_name,
        )

        if timeout is not None:
            return await asyncio.wait_for(future, timeout)
        return await future
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
