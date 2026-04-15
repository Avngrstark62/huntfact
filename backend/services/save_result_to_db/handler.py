from typing import Tuple, Optional
from logging_config import get_logger
from services.save_result_to_db.save_result_to_db import save_result_to_db
from rmq.schemas import TaskMessage
from rmq.constants import NOTIFY

logger = get_logger("services.save_result_to_db.handler")


async def handle_save_result_to_db(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Save result to database.
    
    Takes result from job state and saves it to the database using hunt_id from state.
    """
    logger.info(f"Starting save result to database for job: {job_id}")
    
    result = job_state.get("result")
    hunt_id = job_state.get("hunt_id")
    
    if not result:
        logger.error(f"No result found in job state for job_id: {job_id}")
        return job_state, None
    
    if not hunt_id:
        logger.error(f"No hunt_id found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Saving result for job_id: {job_id}, hunt_id: {hunt_id}")
    
    await save_result_to_db(hunt_id, result)
    
    logger.info(f"Result saved for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=NOTIFY,
        priority=12,
        payload={}
    )
    
    return job_state, task
