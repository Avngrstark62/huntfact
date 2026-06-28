import asyncio
import json
import logging
import uuid

import aio_pika

from rmq.connection import rabbitmq
from config import settings
from rmq.schemas import (
    TaskMessage,
    TaskRpcResponse,
    WorkflowMessage,
    parse_task_rpc_response,
)
from logging_config import get_logger, log_event

logger = get_logger("rmq.publisher")


def _task_queue_arguments() -> dict:
    return {
        "x-max-priority": settings.rabbitmq.max_priority,
        "x-dead-letter-exchange": settings.rabbitmq.dead_letter_exchange_name,
        "x-dead-letter-routing-key": settings.rabbitmq.task_dead_letter_routing_key,
    }


def _workflow_queue_arguments() -> dict:
    return {
        "x-dead-letter-exchange": settings.rabbitmq.dead_letter_exchange_name,
        "x-dead-letter-routing-key": settings.rabbitmq.workflow_dead_letter_routing_key,
    }


async def publish_task(task: TaskMessage):
    channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)
    context = task.payload.get("context") if isinstance(task.payload, dict) else {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="rmq.publish.started",
        status="started",
        message="Publishing task message",
        component="rmq.publisher",
        queue=settings.rabbitmq.task_queue_name,
        routing_key=settings.rabbitmq.task_queue_name,
        step=task.step,
        workflow_id=context.get("workflow_id"),
        hunt_id=context.get("hunt_id"),
        task_id=context.get("task_id"),
        request_id=context.get("request_id"),
    )

    try:
        await channel.declare_queue(
            settings.rabbitmq.task_queue_name,
            durable=True,
            arguments=_task_queue_arguments(),
        )

        message = aio_pika.Message(
            body=json.dumps(task.model_dump()).encode(),
            priority=task.priority,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.rabbitmq.task_queue_name
        )
        log_event(
            logger,
            level=logging.INFO,
            event="rmq.publish.succeeded",
            status="succeeded",
            message="Published task message",
            component="rmq.publisher",
            queue=settings.rabbitmq.task_queue_name,
            routing_key=settings.rabbitmq.task_queue_name,
            step=task.step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            task_id=context.get("task_id"),
            request_id=context.get("request_id"),
        )
    except Exception as exc:
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.publish.failed",
            status="failed",
            message="Failed to publish task message",
            component="rmq.publisher",
            queue=settings.rabbitmq.task_queue_name,
            routing_key=settings.rabbitmq.task_queue_name,
            step=task.step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            task_id=context.get("task_id"),
            request_id=context.get("request_id"),
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )
        raise
    finally:
        await channel.close()


async def publish_task_rpc(task: TaskMessage, *, timeout: float | None = None) -> TaskRpcResponse:
    """
    Publish a task and await the worker reply via RabbitMQ direct reply-to (RPC-style).

    Returns the validated RPC response envelope from the worker response.
    Raises asyncio.TimeoutError if timeout is set and no reply arrives in time.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    correlation_id = str(uuid.uuid4())
    context = task.payload.get("context") if isinstance(task.payload, dict) else {}
    context = context if isinstance(context, dict) else {}

    async def on_response(message: aio_pika.IncomingMessage):
        try:
            if str(message.correlation_id or "") != correlation_id:
                return
            body = json.loads(message.body.decode())
            parsed_response = parse_task_rpc_response(body)
            if not future.done():
                future.set_result(parsed_response)
            log_event(
                logger,
                level=logging.INFO,
                event="rmq.rpc.reply.received",
                status="succeeded",
                message="Received RPC reply",
                component="rmq.publisher",
                correlation_id=correlation_id,
                queue=settings.rabbitmq.task_queue_name,
                step=task.step,
                workflow_id=context.get("workflow_id"),
                hunt_id=context.get("hunt_id"),
                task_id=context.get("task_id"),
                request_id=context.get("request_id"),
            )
        except Exception as e:
            if not future.done():
                future.set_exception(e)
            log_event(
                logger,
                level=logging.ERROR,
                event="rmq.rpc.reply.failed",
                status="failed",
                message="Failed to parse RPC reply",
                component="rmq.publisher",
                correlation_id=correlation_id,
                queue=settings.rabbitmq.task_queue_name,
                step=task.step,
                workflow_id=context.get("workflow_id"),
                hunt_id=context.get("hunt_id"),
                task_id=context.get("task_id"),
                request_id=context.get("request_id"),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )

    channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)

    try:
        log_event(
            logger,
            level=logging.INFO,
            event="rmq.publish.started",
            status="started",
            message="Publishing RPC task message",
            component="rmq.publisher",
            queue=settings.rabbitmq.task_queue_name,
            routing_key=settings.rabbitmq.task_queue_name,
            correlation_id=correlation_id,
            step=task.step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            task_id=context.get("task_id"),
            request_id=context.get("request_id"),
        )
        await channel.set_qos(prefetch_count=1)

        reply_queue = await channel.declare_queue(
            "amq.rabbitmq.reply-to",
            passive=True,
        )

        await reply_queue.consume(on_response, no_ack=True)

        await channel.declare_queue(
            settings.rabbitmq.task_queue_name,
            durable=True,
            arguments=_task_queue_arguments(),
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
            routing_key=settings.rabbitmq.task_queue_name,
        )
        log_event(
            logger,
            level=logging.INFO,
            event="rmq.publish.succeeded",
            status="succeeded",
            message="Published RPC task message",
            component="rmq.publisher",
            queue=settings.rabbitmq.task_queue_name,
            routing_key=settings.rabbitmq.task_queue_name,
            correlation_id=correlation_id,
            step=task.step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            task_id=context.get("task_id"),
            request_id=context.get("request_id"),
        )

        if timeout is not None:
            return await asyncio.wait_for(future, timeout)
        return await future
    except Exception as exc:
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.publish.failed",
            status="failed",
            message="Failed to publish RPC task message",
            component="rmq.publisher",
            queue=settings.rabbitmq.task_queue_name,
            routing_key=settings.rabbitmq.task_queue_name,
            correlation_id=correlation_id,
            step=task.step,
            workflow_id=context.get("workflow_id"),
            hunt_id=context.get("hunt_id"),
            task_id=context.get("task_id"),
            request_id=context.get("request_id"),
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )
        raise
    finally:
        await channel.close()


async def publish_workflow(workflow: WorkflowMessage):
    channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)
    context = workflow.payload.get("context") if isinstance(workflow.payload, dict) else {}
    context = context if isinstance(context, dict) else {}
    log_event(
        logger,
        level=logging.INFO,
        event="rmq.publish.started",
        status="started",
        message="Publishing workflow message",
        component="rmq.publisher",
        queue=settings.rabbitmq.workflow_queue_name,
        routing_key=settings.rabbitmq.workflow_queue_name,
        workflow_id=workflow.workflow_id,
        hunt_id=context.get("hunt_id"),
        request_id=context.get("request_id"),
    )

    try:
        await channel.declare_queue(
            settings.rabbitmq.workflow_queue_name,
            durable=True,
            arguments=_workflow_queue_arguments(),
        )

        message = aio_pika.Message(
            body=json.dumps(workflow.model_dump()).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.rabbitmq.workflow_queue_name,
        )
        log_event(
            logger,
            level=logging.INFO,
            event="rmq.publish.succeeded",
            status="succeeded",
            message="Published workflow message",
            component="rmq.publisher",
            queue=settings.rabbitmq.workflow_queue_name,
            routing_key=settings.rabbitmq.workflow_queue_name,
            workflow_id=workflow.workflow_id,
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
        )
    except Exception as exc:
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.publish.failed",
            status="failed",
            message="Failed to publish workflow message",
            component="rmq.publisher",
            queue=settings.rabbitmq.workflow_queue_name,
            routing_key=settings.rabbitmq.workflow_queue_name,
            workflow_id=workflow.workflow_id,
            hunt_id=context.get("hunt_id"),
            request_id=context.get("request_id"),
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
        )
        raise
    finally:
        await channel.close()
