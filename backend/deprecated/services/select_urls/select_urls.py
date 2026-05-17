from typing import List, Dict, Any
from logging_config import get_logger
from config import settings
from llm import llm
from pydantic import BaseModel
from urllib.parse import urlparse

logger = get_logger("services.select_urls.select_urls")


class SelectedUrlItem(BaseModel):
    query: str
    selected_indices: List[int]


class BatchSelectedUrlsResponse(BaseModel):
    items: List[SelectedUrlItem]


async def select_urls(items_with_urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Select top 3 most credible and diverse URLs for each item (batch processing).
    
    Uses LLM in a single batch call to analyze all items and select the best sources.
    Prioritizes credibility and domain diversity across all items simultaneously.
    
    Args:
        items_with_urls: List of item dictionaries with query and urls fields
                        Each url object contains: href (url), title, body (snippet)
    
    Returns:
        List of items with selected_urls field containing top 3 URLs
    """
    logger.info(f"Selecting URLs for {len(items_with_urls)} items (batch processing)")
    
    if not items_with_urls:
        logger.warning("No items to process")
        return []
    
    items_to_process = []
    items_to_passthrough = []
    
    for item in items_with_urls:
        urls = item.get("urls", [])
        if not urls:
            logger.warning(f"No URLs for query: {item.get('query', 'unknown')}")
            item["selected_urls"] = []
            items_to_passthrough.append(item)
        elif len(urls) <= 3:
            logger.info(f"Query '{item.get('query')}' has {len(urls)} URLs, selecting all")
            selected = [u.get("href") for u in urls]
            item["selected_urls"] = selected
            items_to_passthrough.append(item)
        else:
            items_to_process.append(item)
    
    if not items_to_process:
        logger.info("No items need URL selection (all have <=3 URLs or no URLs)")
        return items_with_urls
    
    try:
        selected_items = await _batch_select_best_urls(items_to_process)
        
        result = items_to_passthrough + selected_items
        logger.info(f"Selected URLs for {len(result)} items")
        return result
    except Exception as e:
        logger.error(f"Error during batch URL selection: {str(e)}", exc_info=True)
        for item in items_to_process:
            urls = item.get("urls", [])
            item["selected_urls"] = [u.get("href") for u in urls[:3]]
        return items_with_urls


async def _batch_select_best_urls(items_with_urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use LLM to intelligently select top 3 URLs for multiple items in a single batch call.
    
    Args:
        items_with_urls: List of items with urls that need selection
    
    Returns:
        List of items with selected_urls field populated
    """
    items_text = "\n".join([
        _format_item_for_llm(item)
        for item in items_with_urls
    ])
    
    prompt = f"""You are an expert at evaluating and selecting the most credible and relevant sources for fact-checking.

TASK:
Given multiple queries with their corresponding search results, select exactly 3 URL indices for EACH query that are:
1. Most relevant to the query
2. From highly credible sources
3. From different domains (no two URLs for the same query should share the same domain/website)

CREDIBILITY HIERARCHY (High to Low):
1. HIGHEST CREDIBILITY:
   - Official government websites (.gov domains, official ministry sites)
   - Academic institutions (.edu domains, university research)
   - WHO, UN, and international organization official sites
   - Major established news organizations (Reuters, AP, BBC, NPR, etc.)
   - Official company/organization domains
   - Peer-reviewed research and publications

2. MEDIUM CREDIBILITY:
   - Established news outlets and journalistic sources
   - Well-known educational platforms
   - Industry-specific authoritative sources
   - Professional organizations and associations

3. LOW CREDIBILITY (Avoid if possible):
   - Wikipedia and general encyclopedias (secondary sources)
   - Social media platforms (Twitter, Facebook, Reddit, etc.)
   - Forums and discussion boards
   - Blogs and personal websites
   - Content aggregators and listicle sites
   - Sources with obvious bias or sensationalism

DIVERSITY REQUIREMENT:
- For each query, all 3 selected URLs MUST be from different domains/websites
- Do NOT select multiple results from the same website for the same query
- Vary the types of sources (e.g., mix official + news + research)

RELEVANCE PRINCIPLE:
- URLs must directly address the query/question
- Titles should indicate substantive information related to the query
- Avoid tangential or loosely related results

SELECTION STRATEGY:
1. For each query, identify all URLs with high credibility sources
2. From those, pick diverse domains (different websites)
3. Ensure all 3 are highly relevant to the query
4. If high-credibility sources don't exist, use medium-credibility but maintain diversity and relevance

ITEMS TO PROCESS:
{items_text}

For each query, return exactly 3 indices from the available URLs (0-indexed). Return the indices as a JSON list."""
    
    messages = [
        {
            "role": "system",
            "content": "You are a fact-checking assistant that selects the most credible and diverse sources from search results. You understand source credibility, domain diversity, and relevance to fact-checking queries. You can handle multiple queries simultaneously and apply consistent selection criteria across them."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    try:
        result = await llm.call_with_schema(
            model=settings.reasoning_model,
            messages=messages,
            schema_model=BatchSelectedUrlsResponse,
        )
        
        for item in items_with_urls:
            query = item.get("query", "")
            urls = item.get("urls", [])
            
            selected_item = next(
                (s for s in result.items if s.query == query),
                None
            )
            
            if selected_item:
                selected = [
                    urls[idx].get("href")
                    for idx in selected_item.selected_indices
                    if idx < len(urls)
                ]
                item["selected_urls"] = selected
            else:
                logger.warning(f"No selection found for query: {query}")
                item["selected_urls"] = []
        
        logger.info(f"Batch selected URLs for {len(items_with_urls)} items")
        
        return items_with_urls
    except Exception as e:
        logger.error(f"Failed to batch select URLs using LLM: {str(e)}", exc_info=True)
        raise


def _format_item_for_llm(item: Dict[str, Any]) -> str:
    """
    Format a single item with its URLs in compact form for LLM processing.
    
    Format: [{index}] {domain} | {title}
    
    Args:
        item: Item dictionary with query and urls
    
    Returns:
        Formatted string for LLM
    """
    query = item.get("query", "")
    urls = item.get("urls", [])
    
    urls_text = "\n".join([
        f"  [{idx}] {_extract_domain(u.get('href', ''))} | {u.get('title', '')}"
        for idx, u in enumerate(urls)
    ])
    
    return f"QUERY: {query}\nURLs:\n{urls_text}"


def _extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL string
    
    Returns:
        Domain name (e.g., 'wikipedia.org', 'bbc.co.uk')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url

