import asyncio
from datetime import datetime, UTC
import json
import logging

import aio_pika
from pydantic import ValidationError

from logging_config import get_logger, log_event

from rmq.connection import rabbitmq
from config import settings
from rmq.schemas import TaskMessage, WorkflowMessage

logger = get_logger("rmq.consumer")
RECONNECT_DELAY_SECONDS = 5


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


def _decode_message_body(raw_message: aio_pika.IncomingMessage) -> str:
    try:
        return raw_message.body.decode("utf-8")
    except UnicodeDecodeError:
        return raw_message.body.decode("utf-8", errors="replace")


def _message_id(raw_message: aio_pika.IncomingMessage) -> str | None:
    value = raw_message.message_id
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _correlation_id(raw_message: aio_pika.IncomingMessage) -> str | None:
    value = raw_message.correlation_id
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


async def _declare_dead_letter_topology(channel: aio_pika.Channel) -> None:
    dlx = await channel.declare_exchange(
        settings.rabbitmq.dead_letter_exchange_name,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    task_dlq = await channel.declare_queue(
        settings.rabbitmq.task_dead_letter_queue_name,
        durable=True,
    )
    workflow_dlq = await channel.declare_queue(
        settings.rabbitmq.workflow_dead_letter_queue_name,
        durable=True,
    )
    await task_dlq.bind(dlx, routing_key=settings.rabbitmq.task_dead_letter_routing_key)
    await workflow_dlq.bind(dlx, routing_key=settings.rabbitmq.workflow_dead_letter_routing_key)


async def _publish_poison_message(
    channel: aio_pika.Channel,
    *,
    routing_key: str,
    reason: str,
    error: str,
    raw_message: aio_pika.IncomingMessage,
) -> None:
    payload = {
        "reason": reason,
        "error": error,
        "original": {
            "body": _decode_message_body(raw_message),
            "message_id": _message_id(raw_message),
            "correlation_id": _correlation_id(raw_message),
            "routing_key": raw_message.routing_key,
            "headers": dict(raw_message.headers or {}),
        },
        "captured_at": datetime.now(UTC).isoformat(),
    }
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload, default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key=routing_key,
    )


async def _quarantine_message(
    channel: aio_pika.Channel,
    *,
    routing_key: str,
    reason: str,
    error: str,
    raw_message: aio_pika.IncomingMessage,
    consumer_name: str,
) -> None:
    try:
        await _publish_poison_message(
            channel,
            routing_key=routing_key,
            reason=reason,
            error=error,
            raw_message=raw_message,
        )
        await raw_message.ack()
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.message.quarantined",
            status="quarantined",
            message="Message quarantined",
            component="rmq.consumer",
            queue=routing_key,
            routing_key=raw_message.routing_key,
            message_id=_message_id(raw_message),
            correlation_id=_correlation_id(raw_message),
            error_message=error,
            reason=reason,
        )
    except Exception as quarantine_error:
        log_event(
            logger,
            level=logging.ERROR,
            event="rmq.message.rejected",
            status="failed",
            message="Failed to quarantine message; rejecting without requeue",
            component="rmq.consumer",
            queue=routing_key,
            routing_key=raw_message.routing_key,
            message_id=_message_id(raw_message),
            correlation_id=_correlation_id(raw_message),
            error_type=type(quarantine_error).__name__,
            error_message=str(quarantine_error),
            exc_info=True,
        )
        await raw_message.reject(requeue=False)


async def start_task_consumer(handler):
    while True:
        channel = None
        try:
            channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)
            await _declare_dead_letter_topology(channel)
            queue = await channel.declare_queue(
                settings.rabbitmq.task_queue_name,
                durable=True,
                arguments=_task_queue_arguments(),
            )
            log_event(
                logger,
                level=logging.INFO,
                event="rmq.consume.started",
                status="started",
                message="Started consuming task queue",
                component="rmq.consumer",
                queue=settings.rabbitmq.task_queue_name,
            )

            async with queue.iterator() as queue_iter:
                async for raw_message in queue_iter:
                    try:
                        log_event(
                            logger,
                            level=logging.INFO,
                            event="rmq.message.received",
                            status="started",
                            message="Task message received",
                            component="rmq.consumer",
                            queue=settings.rabbitmq.task_queue_name,
                            routing_key=raw_message.routing_key,
                            message_id=_message_id(raw_message),
                            correlation_id=_correlation_id(raw_message),
                            delivery_tag=raw_message.delivery_tag,
                            redelivered=raw_message.redelivered,
                        )
                        body = _decode_message_body(raw_message)
                        try:
                            msg = json.loads(body)
                        except json.JSONDecodeError as decode_error:
                            await _quarantine_message(
                                channel,
                                routing_key=settings.rabbitmq.task_dead_letter_queue_name,
                                reason="invalid_json",
                                error=str(decode_error),
                                raw_message=raw_message,
                                consumer_name="TASK_CONSUMER",
                            )
                            continue

                        try:
                            validated = TaskMessage.model_validate(msg)
                        except ValidationError as validation_error:
                            await _quarantine_message(
                                channel,
                                routing_key=settings.rabbitmq.task_dead_letter_queue_name,
                                reason="schema_validation_failed",
                                error=str(validation_error),
                                raw_message=raw_message,
                                consumer_name="TASK_CONSUMER",
                            )
                            continue

                        await handler(validated.model_dump(), raw_message)
                        await raw_message.ack()
                        log_event(
                            logger,
                            level=logging.INFO,
                            event="rmq.message.acked",
                            status="succeeded",
                            message="Task message acknowledged",
                            component="rmq.consumer",
                            queue=settings.rabbitmq.task_queue_name,
                            routing_key=raw_message.routing_key,
                            message_id=_message_id(raw_message),
                            correlation_id=_correlation_id(raw_message),
                            delivery_tag=raw_message.delivery_tag,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        await _quarantine_message(
                            channel,
                            routing_key=settings.rabbitmq.task_dead_letter_queue_name,
                            reason="handler_exception",
                            error=str(e),
                            raw_message=raw_message,
                            consumer_name="TASK_CONSUMER",
                        )
                        continue
        except asyncio.CancelledError:
            log_event(
                logger,
                level=logging.INFO,
                event="rmq.consume.started",
                status="cancelled",
                message="Task consumer cancellation requested",
                component="rmq.consumer",
                queue=settings.rabbitmq.task_queue_name,
            )
            raise
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="rmq.consume.started",
                status="retrying",
                message="Task consumer loop failed; reconnecting",
                component="rmq.consumer",
                queue=settings.rabbitmq.task_queue_name,
                delay_seconds=RECONNECT_DELAY_SECONDS,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        finally:
            if channel is not None:
                try:
                    await channel.close()
                except Exception:
                    pass


async def start_workflow_consumer(handler):
    while True:
        channel = None
        try:
            channel = await rabbitmq.get_channel(settings.rabbitmq.prefetch_count)
            await _declare_dead_letter_topology(channel)
            queue = await channel.declare_queue(
                settings.rabbitmq.workflow_queue_name,
                durable=True,
                arguments=_workflow_queue_arguments(),
            )
            log_event(
                logger,
                level=logging.INFO,
                event="rmq.consume.started",
                status="started",
                message="Started consuming workflow queue",
                component="rmq.consumer",
                queue=settings.rabbitmq.workflow_queue_name,
            )

            async with queue.iterator() as queue_iter:
                async for raw_message in queue_iter:
                    try:
                        log_event(
                            logger,
                            level=logging.INFO,
                            event="rmq.message.received",
                            status="started",
                            message="Workflow message received",
                            component="rmq.consumer",
                            queue=settings.rabbitmq.workflow_queue_name,
                            routing_key=raw_message.routing_key,
                            message_id=_message_id(raw_message),
                            correlation_id=_correlation_id(raw_message),
                            delivery_tag=raw_message.delivery_tag,
                            redelivered=raw_message.redelivered,
                        )
                        body = _decode_message_body(raw_message)
                        try:
                            msg = json.loads(body)
                        except json.JSONDecodeError as decode_error:
                            await _quarantine_message(
                                channel,
                                routing_key=settings.rabbitmq.workflow_dead_letter_queue_name,
                                reason="invalid_json",
                                error=str(decode_error),
                                raw_message=raw_message,
                                consumer_name="WORKFLOW_CONSUMER",
                            )
                            continue

                        try:
                            validated = WorkflowMessage.model_validate(msg)
                        except ValidationError as validation_error:
                            await _quarantine_message(
                                channel,
                                routing_key=settings.rabbitmq.workflow_dead_letter_queue_name,
                                reason="schema_validation_failed",
                                error=str(validation_error),
                                raw_message=raw_message,
                                consumer_name="WORKFLOW_CONSUMER",
                            )
                            continue

                        await handler(validated.model_dump())
                        await raw_message.ack()
                        log_event(
                            logger,
                            level=logging.INFO,
                            event="rmq.message.acked",
                            status="succeeded",
                            message="Workflow message acknowledged",
                            component="rmq.consumer",
                            queue=settings.rabbitmq.workflow_queue_name,
                            routing_key=raw_message.routing_key,
                            message_id=_message_id(raw_message),
                            correlation_id=_correlation_id(raw_message),
                            delivery_tag=raw_message.delivery_tag,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        await _quarantine_message(
                            channel,
                            routing_key=settings.rabbitmq.workflow_dead_letter_queue_name,
                            reason="handler_exception",
                            error=str(e),
                            raw_message=raw_message,
                            consumer_name="WORKFLOW_CONSUMER",
                        )
                        continue
        except asyncio.CancelledError:
            log_event(
                logger,
                level=logging.INFO,
                event="rmq.consume.started",
                status="cancelled",
                message="Workflow consumer cancellation requested",
                component="rmq.consumer",
                queue=settings.rabbitmq.workflow_queue_name,
            )
            raise
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="rmq.consume.started",
                status="retrying",
                message="Workflow consumer loop failed; reconnecting",
                component="rmq.consumer",
                queue=settings.rabbitmq.workflow_queue_name,
                delay_seconds=RECONNECT_DELAY_SECONDS,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        finally:
            if channel is not None:
                try:
                    await channel.close()
                except Exception:
                    pass
