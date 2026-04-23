import json
from typing import Any, Optional

from logging_config import get_logger

logger = get_logger("redis.codec")


def dumps(value: Any) -> str:
    return json.dumps(value)


def loads(value: Optional[str]) -> Any:
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.error("Failed to decode Redis JSON payload", exc_info=True)
        return None
