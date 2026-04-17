from typing import Tuple, Optional, List, Dict, Any
from logging_config import get_logger
from services.fetch_urls.fetch_urls import fetch_urls_for_queries
from rmq.schemas import TaskMessage
from rmq.constants import SELECT_URLS

logger = get_logger("services.fetch_urls.handler")


async def handle_fetch_urls(job_id: str, job_state: dict) -> Tuple[dict, Optional[TaskMessage]]:
    """
    Fetch URLs for extracted questions/queries.
    
    Fetches URLs from the web for each query in items and returns updated state
    with URLs added to each item, along with the next task message.
    
    Args:
        job_id: Unique job identifier
        job_state: Current job state dict
    
    Returns:
        Tuple of (updated_state, next_task_message)
    """
    logger.info(f"Starting URL fetching for job: {job_id}")
    
    # Get items from state
    items = job_state.get("items")
    
    if not items:
        logger.error(f"No items found in job state for job_id: {job_id}")
        return job_state, None
    
    # Extract queries from items
    queries = [item.get("query") for item in items if item.get("query")]
    
    if not queries:
        logger.error(f"No queries found in items for job_id: {job_id}")
        return job_state, None
    
    logger.info(f"Fetching URLs for {len(queries)} queries for job_id: {job_id}")
    
    try:
        # Fetch URLs for all queries
        urls_results = await fetch_urls_for_queries(queries)
        
        # Create a mapping of query to urls
        query_to_urls = {result["query"]: result["urls"] for result in urls_results}
        
        # Update items with URLs
        for item in items:
            query = item.get("query")
            if query in query_to_urls:
                item["urls"] = query_to_urls[query]
            else:
                item["urls"] = []
        
        # Update job state with items that now have URLs
        job_state["items"] = items
        
        logger.info(f"URL fetching completed for job_id: {job_id}")
    except Exception as e:
        logger.error(f"Error fetching URLs for job_id: {job_id}: {str(e)}", exc_info=True)
        return job_state, None
    
    # Create next task for selecting URLs
    task = TaskMessage(
        job_id=job_id,
        step=SELECT_URLS,
        priority=6,
        payload={}
    )
    
    return job_state, task
