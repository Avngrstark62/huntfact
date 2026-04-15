from typing import Tuple, Optional
from logging_config import get_logger
from services.translator.translator import translate_utterances
from rmq.schemas import TaskMessage
from rmq.constants import EXTRACT_QUESTIONS_QUERIES

logger = get_logger("services.translator.handler")


async def handle_translate(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Translate utterances to English.
    
    Translates utterances from the state and returns updated state
    with translated utterances stored as utterances_english, along with the next task message.
    
    Args:
        job_id: Unique job identifier
        job_state: Current job state dict
    
    Returns:
        Tuple of (updated_state, next_task_message)
    """
    logger.info(f"Starting translation for job: {job_id}")
    
    # Get utterances from state
    utterances = job_state.get("utterances")
    
    if not utterances:
        logger.error(f"No utterances found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Translating {len(utterances)} utterances for job_id: {job_id}")
    
    # Translate utterances
    translated_utterances = await translate_utterances(utterances)
    
    # Update job state with translated utterances
    job_state["utterances_english"] = translated_utterances
    
    logger.info(f"Translation completed for job_id: {job_id}")
    
    # Create next task for extracting questions/queries
    task = TaskMessage(
        job_id=job_id,
        step=EXTRACT_QUESTIONS_QUERIES,
        priority=4,
        payload={}
    )
    
    return job_state, task
