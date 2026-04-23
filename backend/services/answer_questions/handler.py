from typing import Optional
from logging_config import get_logger
from services.answer_questions.answer_questions import answer_questions
from rmq.schemas import TaskMessage
from rmq.constants import GENERATE_RESULT
from rmq_redis import job_repository

logger = get_logger("services.answer_questions.handler")


async def handle_answer_questions(job_id: str) -> Optional[TaskMessage]:
    """
    Answer questions using RAG-retrieved chunks.
    
    Fetches chunks from RAG for each question and sends to LLM for answering.
    """
    logger.info(f"Starting question answering for job: {job_id}")
    
    items = job_repository.get_composed_items(job_id)
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Answering questions for {len(items)} items for job_id: {job_id}")
    
    try:
        items_with_answers = await answer_questions(job_id, items)
        for item in items_with_answers:
            job_repository.set_item_answer(job_id, item["item_id"], item.get("answer"))
        
        logger.info(f"Question answering completed for job_id: {job_id}")
    except Exception as e:
        logger.error(f"Error answering questions for job_id: {job_id}: {str(e)}", exc_info=True)
        return None
    
    task = TaskMessage(
        job_id=job_id,
        step=GENERATE_RESULT,
        priority=10,
        payload={}
    )
    
    return task
