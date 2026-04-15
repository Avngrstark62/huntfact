from typing import Tuple, Optional
from logging_config import get_logger
from services.extract_questions_queries.extract_questions_queries import extract_questions_queries
from rmq.schemas import TaskMessage
from rmq.constants import FETCH_URLS

logger = get_logger("services.extract_questions_queries.handler")


async def handle_extract_questions_queries(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Extract questions and queries from English utterances.
    
    Extracts questions and queries from the state and returns updated state
    with extracted items, along with the next task message.
    
    Args:
        job_id: Unique job identifier
        job_state: Current job state dict
    
    Returns:
        Tuple of (updated_state, next_task_message)
    """
    logger.info(f"Starting question/query extraction for job: {job_id}")
    
    # Get utterances_english from state
    utterances_english = job_state.get("utterances_english")
    
    if not utterances_english:
        logger.error(f"No utterances_english found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Extracting questions/queries from {len(utterances_english)} English utterances for job_id: {job_id}")
    
    # Extract questions and queries
    items = await extract_questions_queries(utterances_english)
    
    # Update job state with extracted items
    job_state["items"] = items
    
    logger.info(f"Question/query extraction completed for job_id: {job_id}, extracted {len(items)} items")
    
    # Create next task for fetching URLs
    task = TaskMessage(
        job_id=job_id,
        step=FETCH_URLS,
        priority=5,
        payload={}
    )
    
    return job_state, task
