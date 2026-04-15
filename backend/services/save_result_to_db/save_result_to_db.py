from typing import Dict, Any
import json
from logging_config import get_logger
from db.database import db

logger = get_logger("services.save_result_to_db.save_result_to_db")


async def save_result_to_db(hunt_id: int, result: Dict[str, Any]) -> None:
    """
    Save result to database.
    
    Takes the hunt_id and result, stores it in the database as JSON.
    
    Args:
        hunt_id: Hunt ID to associate with the result
        result: Final result dictionary with verdict, confidence, explanation, sources
    """
    logger.info(f"Saving result to database for hunt_id: {hunt_id}")
    
    try:
        session = db.SessionLocal()
        
        result_json = json.dumps(result)
        db.update_hunt_result(session, hunt_id, result_json)
        
        logger.info(f"Result saved successfully for hunt_id: {hunt_id}")
        session.close()
    except Exception as e:
        logger.error(f"Error saving result to database: {e}", exc_info=True)
        raise
