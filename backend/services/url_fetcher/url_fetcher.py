import asyncio
from typing import Any, Dict, List

import requests
from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger

logger = get_logger("services.url_fetcher.url_fetcher")
INTER_QUERY_DELAY_SECONDS = 2


class QueryListResponse(BaseModel):
    queries: List[str]


def _normalize_queries(queries: List[str]) -> List[str]:
    normalized_queries: List[str] = []
    seen_queries: set[str] = set()

    for query in queries:
        cleaned_query = query.strip()
        if not cleaned_query:
            continue
        if cleaned_query in seen_queries:
            continue

        seen_queries.add(cleaned_query)
        normalized_queries.append(cleaned_query)

        if len(normalized_queries) == 5:
            break

    return normalized_queries


async def _generate_web_queries(claims: List[str]) -> List[str]:
    claims_text = "\n".join([f"- {claim}" for claim in claims])
    prompt = f"""You are given a list of closely related factual claims that need web verification.

Your task:
- Produce the minimum number of search-engine queries needed to verify all claims.
- Return at least 1 and at most 3 queries.
- Queries should be practical Google-style searches likely to surface authoritative context pages.
- Prefer concise keyword-focused phrasing.
- Include key entities, dates, locations, and claim-specific terms when needed.
- Avoid duplicate or near-duplicate queries.

Claims:
{claims_text}
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a web-research assistant that writes high-quality search queries "
                "to verify factual claims. Return only the structured output."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    result = await llm.call_with_schema(
        model=settings.models.reasoning_model,
        messages=messages,
        schema_model=QueryListResponse,
    )

    normalized_queries = _normalize_queries(result.queries)
    if normalized_queries:
        return normalized_queries

    # Keep a safe fallback to preserve the 1..5 contract.
    return [claims[0]]


def _extract_search_results(search_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    extracted_results: List[Dict[str, str]] = []
    seen_links: set[str] = set()

    for result in search_results:
        url = str(result.get("url", "")).strip()
        if not url:
            continue
        if url in seen_links:
            continue

        seen_links.add(url)
        extracted_results.append(
            {
                "title": str(result.get("title", "")).strip(),
                "url": url,
            }
        )

    return extracted_results


def _search_web_via_searxng(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            settings.search.searxng_search_url,
            params={"q": query, "format": "json"},
            timeout=settings.search.searxng_timeout_seconds,
        )
    except requests.RequestException as e:
        logger.error(f"SearxNG request failed for query '{query}': {str(e)}", exc_info=True)
        raise RuntimeError(f"SearxNG request failed for query '{query}': {str(e)}") from e

    if response.status_code != 200:
        raise RuntimeError(
            f"SearxNG returned HTTP {response.status_code} for query '{query}': {response.text[:240]}"
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise RuntimeError(f"SearxNG returned invalid JSON for query '{query}'") from e

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise RuntimeError(f"SearxNG response missing 'results' list for query '{query}'")

    normalized_results: List[Dict[str, Any]] = []
    for item in raw_results[:max_results]:
        if not isinstance(item, dict):
            continue
        normalized_results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
            }
        )
    return normalized_results


async def fetch_urls_for_claims(claims: List[str]) -> List[Dict[str, Any]]:
    """
    Generate web queries for related claims and fetch result URLs per query.

    Args:
        claims: List of closely related claims

    Returns:
        [
            {
                "query": "...",
                "urls": [{"title": "...", "url": "..."}, ...],
            },
            ...
        ]
    """
    if not claims:
        logger.warning("No claims provided for URL fetching")
        return []

    cleaned_claims = [claim.strip() for claim in claims if claim and claim.strip()]
    if not cleaned_claims:
        logger.warning("Claims are empty after normalization")
        return []

    logger.info(f"Generating web queries for {len(cleaned_claims)} related claims")
    queries = await _generate_web_queries(cleaned_claims)
    logger.info(f"Generated {len(queries)} web queries for URL fetching")

    results: List[Dict[str, Any]] = []

    for index, query in enumerate(queries):
        logger.info(f"Searching web for query: {query}")
        try:
            search_results = _search_web_via_searxng(query=query, max_results=10)
        except Exception as e:
            logger.error(f"SearxNG web search failed for query '{query}': {str(e)}", exc_info=True)
            raise RuntimeError(f"SearxNG web search failed for query '{query}': {str(e)}") from e

        urls = _extract_search_results(search_results)
        logger.info(f"Found {len(urls)} URLs for query: {query}")
        results.append({"query": query, "urls": urls})

        if index < len(queries) - 1:
            logger.info(
                f"Waiting {INTER_QUERY_DELAY_SECONDS}s before next web search query"
            )
            await asyncio.sleep(INTER_QUERY_DELAY_SECONDS)

    return results
