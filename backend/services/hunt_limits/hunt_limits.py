from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.database import db
from logging_config import get_logger

logger = get_logger("services.hunt_limits.hunt_limits")


def enforce_user_hunt_limit(session: Session, user_id: str) -> JSONResponse | None:
    user_hunts_limit = db.get_or_create_user_hunts_limit(session, user_id)
    active_hunts_count = db.get_active_hunts_count_by_user_id(session, user_id)

    if active_hunts_count >= user_hunts_limit:
        logger.info(
            "Hunt limit reached for user_id=%s active_hunts=%s hunts_limit=%s",
            user_id,
            active_hunts_count,
            user_hunts_limit,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": (
                    f"Hunt limit reached. You have {active_hunts_count} hunts in "
                    f"queued/starting/processing/completed states with a limit of {user_hunts_limit}."
                )
            },
        )

    return None
