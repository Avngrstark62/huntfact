from typing import Optional
from logging_config import get_logger
from services.save_result_to_db.save_result_to_db import save_result_to_db
from rmq.schemas import TaskMessage
from rmq.constants import NOTIFY
from rmq_redis import job_repository

logger = get_logger("services.save_result_to_db.handler")


async def handle_save_result_to_db(job_id: str, payload: dict | None = None) -> Optional[TaskMessage]:
    """
    Save result to database.
    
    Takes result from job state and saves it to the database using hunt_id from state.
    """
    logger.info(f"Starting save result to database for job: {job_id}")
    
    result = job_repository.get_result(job_id)
    hunt_id = job_repository.get_meta_fields(job_id, ["hunt_id"]).get("hunt_id")
    
    if not result:
        logger.error(f"No result found in job state for job_id: {job_id}")
        return None
    
    if not hunt_id:
        logger.error(f"No hunt_id found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Saving result for job_id: {job_id}, hunt_id: {hunt_id}")
    
    await save_result_to_db(int(hunt_id), result)
    
    logger.info(f"Result saved for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=NOTIFY,
        priority=12,
        payload={}
    )
    
    return task
