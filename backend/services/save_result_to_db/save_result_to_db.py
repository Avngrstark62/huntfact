import json
from typing import Any, Dict

from db.database import db
from logging_config import get_logger

logger = get_logger("services.save_result_to_db.save_result_to_db")


async def save_result_to_db(hunt_id: int, table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist claim verifier table in hunts.result as a JSON string.

    Args:
        hunt_id: Target hunt id.
        table: Structured claim-verifier result table.

    Returns:
        Dict with save metadata.
    """
    serialized_result = json.dumps(table, ensure_ascii=False)
    session = db.SessionLocal()

    try:
        updated_hunt = db.update_hunt_result(session, hunt_id, serialized_result)
        if not updated_hunt:
            raise RuntimeError(f"Hunt not found for hunt_id={hunt_id}")

        logger.info(f"Saved result table to DB for hunt_id: {hunt_id}")
        return {
            "hunt_id": hunt_id,
            "result": serialized_result,
        }
    finally:
        session.close()
