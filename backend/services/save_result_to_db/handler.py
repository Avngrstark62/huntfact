from typing import Any, Optional

from logging_config import get_logger
from services.save_result_to_db.save_result_to_db import save_result_to_db

logger = get_logger("services.save_result_to_db.handler")


async def handle_save_result_to_db(payload: dict[str, Any] | None = None) -> Optional[dict]:
    """
    Save claim-verifier table in DB using explicit payload input.

    Expected payload:
        {
            "hunt_id": <int>,
            "table": <dict>
        }
    """
    logger.info("Starting save_result_to_db service")

    raw_hunt_id = (payload or {}).get("hunt_id")
    table = (payload or {}).get("table")

    if not isinstance(raw_hunt_id, int):
        logger.error("Missing or invalid hunt_id in payload")
        return {"saved": None, "error": "Missing or invalid hunt_id in payload"}

    if not isinstance(table, dict):
        logger.error("Missing or invalid table in payload")
        return {"saved": None, "error": "Missing or invalid table in payload"}

    try:
        saved = await save_result_to_db(raw_hunt_id, table)
        logger.info(f"save_result_to_db service completed for hunt_id: {raw_hunt_id}")
        return {"saved": saved, "error": None}
    except Exception as e:
        logger.error(f"save_result_to_db service failed: {str(e)}", exc_info=True)
        return {"saved": None, "error": str(e)}
