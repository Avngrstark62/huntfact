from typing import List, Dict, Any
import json
from logging_config import get_logger
from services.page_scraper import scrape_page

logger = get_logger("services.fetch_pages.fetch_pages")


async def fetch_pages(selected_urls_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fetch and scrape pages from selected URLs.
    
    Scrapes content from all selected URLs across all items and stores
    them in a mocked GCS. Returns a reference to the stored data.
    
    Args:
        selected_urls_list: List of URL dictionaries with title, href, body
    
    Returns:
        Dictionary with GCS reference: {"gcs_reference": "gcs://ref-xyz"}
    """
    logger.info(f"Fetching {len(selected_urls_list)} pages")
    
    pages_data = []
    
    for url_item in selected_urls_list:
        href = url_item.get("href")
        if not href:
            continue
            
        try:
            logger.info(f"Scraping page: {href}")
            result = await scrape_page(href)
            
            if result:
                pages_data.append({
                    "url": href,
                    "title": url_item.get("title", ""),
                    "scraped_content": result
                })
                logger.info(f"Successfully scraped: {href}")
        except Exception as e:
            logger.error(f"Error scraping {href}: {e}")
    
    gcs_reference = f"gcs://huntfact-pages-{hash(json.dumps(str(pages_data))) & 0x7fffffff}"
    
    logger.info(f"Stored {len(pages_data)} pages, GCS reference: {gcs_reference}")
    
    return {
        "gcs_reference": gcs_reference,
        "pages_data": pages_data
    }
