import json
from typing import Any, Dict

from db.database import db
from logging_config import get_logger

logger = get_logger("services.save_result_to_db.save_result_to_db")

DEFAULT_HUNT_TITLE = "This government is responsible for increasing the petrol price overnight."
DEFAULT_HUNT_SUMMARY = (
    "This is a placeholder summary for the hunt result. The actual summary will be generated "
    "by the workflow based on the video content and analysis results."
)
DEFAULT_HUNT_TRUST_SCORE = 47


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
        updated_hunt = db.update_hunt_result(
            session=session,
            hunt_id=hunt_id,
            result=serialized_result,
            title=DEFAULT_HUNT_TITLE,
            summary=DEFAULT_HUNT_SUMMARY,
            trust_score=DEFAULT_HUNT_TRUST_SCORE,
        )
        if not updated_hunt:
            raise RuntimeError(f"Hunt not found for hunt_id={hunt_id}")

        logger.info(f"Saved result table to DB for hunt_id: {hunt_id}")
        return {
            "hunt_id": hunt_id,
            "result": serialized_result,
            "title": updated_hunt.title,
            "summary": updated_hunt.summary,
            "trust_score": updated_hunt.trust_score,
        }
    finally:
        session.close()
