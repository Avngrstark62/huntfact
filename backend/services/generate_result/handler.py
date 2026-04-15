from typing import Tuple, Optional
from logging_config import get_logger
from services.generate_result.generate_result import generate_result
from rmq.schemas import TaskMessage
from rmq.constants import SAVE_RESULT_TO_DB

logger = get_logger("services.generate_result.handler")


async def handle_generate_result(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Generate final result.
    
    Takes questions, answers, and utterances to generate final result
    with verdict, confidence, explanation and sources.
    """
    logger.info(f"Starting result generation for job: {job_id}")
    
    items = job_state.get("items")
    utterances_english = job_state.get("utterances_english")
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return job_state, None
    
    if not utterances_english:
        logger.error(f"No utterances_english found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Generating result for job_id: {job_id}")
    
    result = await generate_result(items, utterances_english)
    
    job_state["result"] = result
    
    logger.info(f"Result generation completed for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=SAVE_RESULT_TO_DB,
        priority=11,
        payload={}
    )
    
    return job_state, task
