from typing import List, Dict, Any
from logging_config import get_logger
from services.page_scraper import scrape_page

logger = get_logger("services.fetch_pages.fetch_pages")


async def fetch_pages(selected_urls_list: List[str]) -> Dict[str, Any]:
    """
    Fetch and scrape pages from selected URLs.
    
    Scrapes content from all selected URLs across all items.
    
    Args:
        selected_urls_list: List of URL strings
    
    Returns:
        Dictionary with pages data: {"pages_data": [...]}
    """
    logger.info(f"Fetching {len(selected_urls_list)} pages")
    
    pages_data = []
    
    for href in selected_urls_list:
        if not href:
            continue
            
        try:
            logger.info(f"Scraping page: {href}")
            result = await scrape_page(href)
            
            if result:
                pages_data.append({
                    "url": href,
                    "scraped_content": result
                })
                logger.info(f"Successfully scraped: {href}")
        except Exception as e:
            logger.error(f"Error scraping {href}: {e}")
    
    logger.info(f"Fetched {len(pages_data)} pages")
    
    return {
        "pages_data": pages_data
    }
