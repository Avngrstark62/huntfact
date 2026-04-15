from typing import List, Dict, Any
from logging_config import get_logger
from services.web_searcher import search_web

logger = get_logger("services.fetch_urls.fetch_urls")


async def fetch_urls_for_queries(queries: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch URLs for a list of queries using web search.
    
    Searches the web for each query and returns a list of results
    where each result contains the query and its corresponding URLs.
    
    Args:
        queries: List of query strings to search for
    
    Returns:
        List of dictionaries with structure:
        [
            {
                "query": "...",
                "urls": [
                    {"title": "...", "href": "...", "body": "..."},
                    ...
                ]
            },
            ...
        ]
    """
    logger.info(f"Fetching URLs for {len(queries)} queries")
    
    results = []
    
    for query in queries:
        try:
            logger.info(f"Searching web for query: {query}")
            
            # Search the web for this query
            urls = search_web(
                query=query,
                max_results=10,
                region="in-en",
                safesearch="moderate",
                timeout=10,
                backend="duckduckgo",
            )
            
            logger.info(f"Found {len(urls)} URLs for query: {query}")
            
            results.append({
                "query": query,
                "urls": urls
            })
        except Exception as e:
            logger.error(f"Error fetching URLs for query '{query}': {e}", exc_info=True)
            results.append({
                "query": query,
                "urls": []
            })
    
    logger.info(f"Completed fetching URLs for all {len(queries)} queries")
    return results
