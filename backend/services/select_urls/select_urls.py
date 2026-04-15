from typing import List, Dict, Any
from logging_config import get_logger

logger = get_logger("services.select_urls.select_urls")


async def select_urls(items_with_urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Select top URLs for each item.
    
    Takes the first 3 URLs from each item's urls list.
    
    Args:
        items_with_urls: List of item dictionaries with urls field
    
    Returns:
        List of items with selected_urls field containing top 3 URLs
    """
    logger.info(f"Selecting URLs for {len(items_with_urls)} items")
    
    result = []
    for item in items_with_urls:
        urls = item.get("urls", [])
        selected = urls[:3]
        item["selected_urls"] = selected
        result.append(item)
    
    logger.info(f"Selected URLs for {len(result)} items")
    return result
