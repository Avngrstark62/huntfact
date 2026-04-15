from typing import Tuple, Optional
from logging_config import get_logger
from services.answer_questions.answer_questions import answer_questions
from rmq.schemas import TaskMessage
from rmq.constants import GENERATE_RESULT

logger = get_logger("services.answer_questions.handler")


async def handle_answer_questions(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Answer questions using RAG-retrieved chunks.
    
    Fetches chunks from RAG for each question and sends to LLM for answering.
    """
    logger.info(f"Starting question answering for job: {job_id}")
    
    items = job_state.get("items")
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Answering questions for {len(items)} items for job_id: {job_id}")
    
    items_with_answers = await answer_questions(items)
    
    job_state["items"] = items_with_answers
    
    logger.info(f"Question answering completed for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=GENERATE_RESULT,
        priority=10,
        payload={}
    )
    
    return job_state, task
