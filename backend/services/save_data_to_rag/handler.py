from typing import Optional
from logging_config import get_logger
from services.save_data_to_rag.save_data_to_rag import save_data_to_rag
from rmq.schemas import TaskMessage
from rmq.constants import ANSWER_QUESTIONS
from rmq_redis import job_repository

logger = get_logger("services.save_data_to_rag.handler")


async def handle_save_data_to_rag(job_id: str) -> Optional[TaskMessage]:
    """
    Save fetched pages to ChromaDB with embeddings.
    
    Fetches page data from job state, chunks it, generates embeddings,
    and ingests into ChromaDB.
    """
    logger.info(f"Starting data save to RAG for job: {job_id}")
    
    pages_data = list(job_repository.iter_pages(job_id))
    
    if not pages_data:
        logger.error(f"No page data found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Retrieved {len(pages_data)} pages for job_id: {job_id}")
    
    try:
        await save_data_to_rag(job_id, pages_data)
    except Exception as e:
        logger.error(f"Failed to save data to RAG for job_id: {job_id}: {str(e)}", exc_info=True)
        return None
    
    job_repository.delete_pages(job_id)
    logger.info(f"Data save to RAG completed for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=ANSWER_QUESTIONS,
        priority=9,
        payload={}
    )
    
    return task

