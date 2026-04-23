from typing import Any, Optional
from logging_config import get_logger
from services.save_data_to_rag.save_data_to_rag import save_data_to_rag
from rmq.schemas import TaskMessage
from rmq.constants import ANSWER_QUESTIONS
from rmq.publisher import publish_task
from rmq_redis import job_repository

logger = get_logger("services.save_data_to_rag.handler")


async def handle_save_data_to_rag(job_id: str, payload: dict[str, Any] | None = None) -> Optional[TaskMessage]:
    """
    Save fetched pages to ChromaDB with embeddings.
    
    Fetches page data from job state, chunks it, generates embeddings,
    and ingests into ChromaDB.
    """
    logger.info(f"Starting data save to RAG for job: {job_id}")
    
    pages_data = list(job_repository.iter_pages(job_id))
    
    if not pages_data:
        logger.error(f"No page data found in job state for job_id: {job_id}")
        raise RuntimeError(f"No page data found for job_id={job_id}")
    
    logger.info(f"Retrieved {len(pages_data)} pages for job_id: {job_id}")
    
    try:
        await save_data_to_rag(job_id, pages_data)
    except Exception as e:
        logger.error(f"Failed to save data to RAG for job_id: {job_id}: {str(e)}", exc_info=True)
        raise
    
    job_repository.delete_pages(job_id)
    item_ids = list(job_repository.iter_item_ids(job_id))
    if not item_ids:
        logger.error(f"No items found in job state for job_id: {job_id}")
        raise RuntimeError(f"No items available for fanout for job_id={job_id}")

    total_items = len(item_ids)
    job_repository.init_qa_barrier(job_id, total_items)
    logger.info(f"Initialized QA fanout barrier for job_id: {job_id}, total: {total_items}")

    for item_id in item_ids:
        await publish_task(
            TaskMessage(
                job_id=job_id,
                step=ANSWER_QUESTIONS,
                priority=9,
                payload={"item_id": item_id},
            )
        )

    logger.info(f"Published QA fanout tasks for job_id: {job_id}, total: {total_items}")
    return None

