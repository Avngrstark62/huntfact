from typing import Optional
from logging_config import get_logger
from services.select_urls.select_urls import select_urls
from rmq.schemas import TaskMessage
from rmq.constants import FETCH_PAGES
from rmq_redis import job_repository

logger = get_logger("services.select_urls.handler")


async def handle_select_urls(job_id: str) -> Optional[TaskMessage]:
    """
    Select top URLs for each question/query item.
    
    Selects the top 3 URLs from the fetched URLs for each item.
    """
    logger.info(f"Starting URL selection for job: {job_id}")
    
    items = job_repository.get_composed_items(job_id)
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return None
    
    logger.info(f"Selecting URLs for {len(items)} items for job_id: {job_id}")
    
    try:
        items_with_selected = await select_urls(items)
        for item in items_with_selected:
            job_repository.set_item_selected_urls(
                job_id,
                item["item_id"],
                item.get("selected_urls", []),
            )
        
        logger.info(f"URL selection completed for job_id: {job_id}")
    except Exception as e:
        logger.error(f"Error selecting URLs for job_id: {job_id}: {str(e)}", exc_info=True)
        return None
    
    task = TaskMessage(
        job_id=job_id,
        step=FETCH_PAGES,
        priority=7,
        payload={}
    )
    
    return task
