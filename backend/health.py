from fastapi import HTTPException, status
from db.database import db
from rmq.connection import rabbitmq


def is_system_healthy() -> bool:
    return db.is_healthy and rabbitmq.is_healthy


async def check_health_dependency():
    if not is_system_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )
