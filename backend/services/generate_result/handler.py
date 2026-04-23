from typing import Optional
from logging_config import get_logger
from services.generate_result.generate_result import generate_result
from rmq.schemas import TaskMessage
from rmq.constants import SAVE_RESULT_TO_DB
from rmq_redis import job_repository

logger = get_logger("services.generate_result.handler")


async def handle_generate_result(job_id: str, payload: dict | None = None) -> Optional[TaskMessage]:
    """
    Generate final result.
    
    Takes questions, answers, and utterances to generate final result
    with verdict, confidence, explanation and sources.
    """
    logger.info(f"Starting result generation for job: {job_id}")
    
    items = job_repository.get_composed_items(job_id)
    utterances_english = job_repository.get_utterances_en(job_id)
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return None
    
    if not utterances_english:
        logger.error(f"No utterances_english found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Generating result for job_id: {job_id}")
    
    try:
        result = await generate_result(items, utterances_english)
        
        if not result:
            logger.error(f"No result generated for job_id: {job_id}")
            return None
        
        job_repository.set_result(job_id, result)
        
        logger.info(f"Result generation completed for job_id: {job_id}")
    except Exception as e:
        logger.error(f"Error generating result for job_id: {job_id}: {str(e)}", exc_info=True)
        return None
    
    task = TaskMessage(
        job_id=job_id,
        step=SAVE_RESULT_TO_DB,
        priority=11,
        payload={}
    )
    
    return task
