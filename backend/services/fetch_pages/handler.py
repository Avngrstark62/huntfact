from typing import Tuple, Optional
from logging_config import get_logger
from services.fetch_pages.fetch_pages import fetch_pages
from rmq.schemas import TaskMessage
from rmq.constants import SAVE_DATA_TO_RAG
from rmq_redis import set_job_data

logger = get_logger("services.fetch_pages.handler")


async def handle_fetch_pages(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Fetch and scrape pages from selected URLs.
    
    Extracts selected URLs from all items, scrapes them, and stores
    to Redis. Updates state with pages data.
    """
    logger.info(f"Starting page fetching for job: {job_id}")
    
    items = job_state.get("items")
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return job_state, None
    
    selected_urls_list = []
    for item in items:
        urls = item.get("selected_urls", [])
        selected_urls_list.extend(urls)
    
    if not selected_urls_list:
        logger.error(f"No selected URLs found for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Fetching {len(selected_urls_list)} pages for job_id: {job_id}")
    
    result = await fetch_pages(selected_urls_list)
    pages_data = result.get("pages_data")
    
    set_job_data(job_id, pages_data)
    job_state["pages_data"] = pages_data
    
    logger.info(f"Page fetching completed for job_id: {job_id}")
    
    task = TaskMessage(
        job_id=job_id,
        step=SAVE_DATA_TO_RAG,
        priority=8,
        payload={}
    )
    
    return job_state, task
