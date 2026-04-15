from typing import Tuple, Optional
from logging_config import get_logger
from services.save_data_to_rag.save_data_to_rag import save_data_to_rag
from rmq.schemas import TaskMessage
from rmq.constants import ANSWER_QUESTIONS

logger = get_logger("services.save_data_to_rag.handler")


async def handle_save_data_to_rag(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Save fetched pages to RAG (mocked).
    
    Takes GCS reference and pages data from state and saves to RAG.
    Updates state with RAG reference.
    """
    logger.info(f"Starting data save to RAG for job: {job_id}")
    
    gcs_reference = job_state.get("gcs_reference")
    pages_data = job_state.get("pages_data", [])
    
    if not gcs_reference:
        logger.error(f"No GCS reference found in job state for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Saving data from GCS to RAG for job_id: {job_id}")
    
    result = await save_data_to_rag(gcs_reference, pages_data)
    
    job_state["rag_reference"] = result.get("rag_reference")
    
    logger.info(f"Data save to RAG completed for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=ANSWER_QUESTIONS,
        priority=9,
        payload={}
    )
    
    return job_state, task
