from fastapi import HTTPException, status
from db.database import db
from rmq.connection import rabbitmq
import logging
from logging_config import get_logger, log_event

logger = get_logger("health")


def is_system_healthy() -> bool:
    return db.is_healthy and rabbitmq.is_healthy


async def check_health_dependency():
    if not is_system_healthy():
        log_event(
            logger,
            level=logging.WARNING,
            event="health.check.failed",
            status="failed",
            message="Health dependency check failed",
            component="api.health",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )
    log_event(
        logger,
        level=logging.INFO,
        event="health.check.succeeded",
        status="succeeded",
        message="Health dependency check succeeded",
        component="api.health",
    )
