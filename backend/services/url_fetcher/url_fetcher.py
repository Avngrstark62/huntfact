import asyncio
import hashlib
import logging
from typing import Any, Dict, List

import requests
from requests.adapters import HTTPAdapter
from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger, log_event

logger = get_logger("services.url_fetcher.url_fetcher")
INTER_QUERY_DELAY_SECONDS = 2
QUERY_PREVIEW_MAX_CHARS = 160
URL_PREVIEW_MAX_CHARS = 220
RESULTS_PREVIEW_QUERY_LIMIT = 3
RESULTS_PREVIEW_URLS_PER_QUERY = 3

# --- Browser-like client setup for SearXNG (anti-bot) ---
# Use ONE stable realistic desktop UA. Do not rotate frequently.
SEARXNG_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

SEARXNG_HEADERS = {
    "User-Agent": SEARXNG_BROWSER_UA,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

_searxng_session: requests.Session | None = None


def _get_searxng_session() -> requests.Session:
    """Return a persistent Session with keep-alive and proper browser headers."""
    global _searxng_session
    if _searxng_session is not None:
        return _searxng_session

    session = requests.Session()
    session.headers.update(SEARXNG_HEADERS)

    # Connection reuse
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    _searxng_session = session
    return _searxng_session


def _query_fingerprint(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]


def _truncate(value: str, max_chars: int) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def _build_results_preview(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    for result in results[:RESULTS_PREVIEW_QUERY_LIMIT]:
        query = str(result.get("query", ""))
        urls = result.get("urls")
        if not isinstance(urls, list):
            urls = []
        preview.append(
            {
                "query": _truncate(query, QUERY_PREVIEW_MAX_CHARS),
                "url_count": len(urls),
                "urls_preview": [
                    {
                        "title": _truncate(str(url.get("title", "")), QUERY_PREVIEW_MAX_CHARS),
                        "url": _truncate(str(url.get("url", "")), URL_PREVIEW_MAX_CHARS),
                    }
                    for url in urls[:RESULTS_PREVIEW_URLS_PER_QUERY]
                    if isinstance(url, dict)
                ],
            }
        )
    return preview


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

        if len(normalized_queries) == 10:
            break

    return normalized_queries


async def _generate_web_queries(claims: List[str]) -> List[str]:
    claims_text = "\n".join([f"- {claim}" for claim in claims])
    prompt = f"""You are given a list of closely related factual claims that need web verification.

Claims:
{claims_text}

Task:
Generate the minimum number of search-engine queries needed to retrieve sufficient evidence to verify all claims.

Algorithm:
1. Read all claims and identify their main entities and topics.
2. Group related claims that can likely be verified using the same evidence.
3. For each group, determine what type of source is most likely to contain authoritative evidence.
4. Generate one search query for each group whenever possible.
5. Include important entities, dates, locations, or technical terms only when they help retrieve more precise evidence.
6. Design queries to retrieve evidence sources rather than general discussions.
7. Avoid duplicate or highly overlapping queries.
8. Stop once all claim groups are covered.

Requirements:
- Produce the minimum number of practical Google-style queries needed to cover all claims.
- Keep queries concise and keyword-focused.
- Return only the structured output.
"""
    messages = [
    {
        "role": "system",
        "content": (
            "You are a web research assistant. "
            "Your objective is to maximize evidence retrieval while minimizing redundant searches. "
            "Follow the provided algorithm exactly. "
            "Return only the requested structured output."
        ),
    },
    {
        "role": "user",
        "content": prompt,
    },
]
#     prompt = f"""You are given a list of closely related factual claims that need web verification.
#
# Your task:
# - Produce the minimum number of search-engine queries needed to verify all claims.
# - Return at least 1 and at most 3 queries.
# - Queries should be practical Google-style searches likely to surface authoritative context pages.
# - Prefer concise keyword-focused phrasing.
# - Include key entities, dates, locations, and claim-specific terms when needed.
# - Avoid duplicate or near-duplicate queries.
#
# Claims:
# {claims_text}
# """
#
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a web-research assistant that writes high-quality search queries "
#                 "to verify factual claims. Return only the structured output."
#             ),
#         },
#         {
#             "role": "user",
#             "content": prompt,
#         },
#     ]
#
    result = await llm.call_with_schema(
        model=settings.llm.reasoning_model,
        messages=messages,
        schema_model=QueryListResponse,
    )

    normalized_queries = _normalize_queries(result.queries)
    if normalized_queries:
        return normalized_queries

    # Keep a safe fallback to preserve the 1..10 contract.
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


def _search_web_via_searxng(
    query: str,
    max_results: int = 10,
    hunt_id: int | None = None,
) -> List[Dict[str, Any]]:
    query_fp = _query_fingerprint(query)
    query_preview = _truncate(query, QUERY_PREVIEW_MAX_CHARS)
    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Starting SearXNG request",
        component="services.url_fetcher",
        provider="searxng",
        operation="search",
        hunt_id=hunt_id,
        query_fingerprint=query_fp,
        query=query_preview,
    )
    session = _get_searxng_session()

    params = {
        "q": query,
        "format": "json",
        "engines": "duckduckgo",
    }

    try:
        response = session.get(
            settings.searxng.url,
            params=params,
            timeout=settings.searxng.timeout,
        )
    except requests.RequestException as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="SearXNG request failed",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
            query=query_preview,
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise RuntimeError(f"SearxNG request failed for query fingerprint '{query_fp}': {str(e)}") from e

    if response.status_code != 200:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="SearXNG returned non-200 response",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
            query=query_preview,
            http_status=response.status_code,
        )
        raise RuntimeError(
            f"SearxNG returned HTTP {response.status_code} for query fingerprint '{query_fp}': {response.text[:240]}"
        )

    try:
        payload = response.json()
    except ValueError as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="SearXNG returned invalid JSON",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
            query=query_preview,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise RuntimeError(f"SearxNG returned invalid JSON for query fingerprint '{query_fp}'") from e

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="SearXNG response missing results list",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
            query=query_preview,
        )
        raise RuntimeError(f"SearxNG response missing 'results' list for query fingerprint '{query_fp}'")

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
    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.succeeded",
        status="succeeded",
        message="SearXNG request succeeded",
        component="services.url_fetcher",
        provider="searxng",
        operation="search",
        hunt_id=hunt_id,
        query_fingerprint=query_fp,
        query=query_preview,
        result_summary={"url_count": len(normalized_results)},
    )
    return normalized_results


async def fetch_urls_for_claims(
    claims: List[str],
    hunt_id: int | None = None,
) -> List[Dict[str, Any]]:
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
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="skipped",
            message="No claims provided for URL fetching",
            component="services.url_fetcher",
            hunt_id=hunt_id,
        )
        return []

    cleaned_claims = [claim.strip() for claim in claims if claim and claim.strip()]
    if not cleaned_claims:
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="skipped",
            message="Claims are empty after normalization",
            component="services.url_fetcher",
            hunt_id=hunt_id,
        )
        return []

    log_event(
        logger,
        level=logging.INFO,
        event="task.started",
        status="started",
        message="Generating web queries",
        component="services.url_fetcher",
        hunt_id=hunt_id,
        result_summary={"claim_count": len(cleaned_claims)},
    )
    queries = await _generate_web_queries(cleaned_claims)
    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Generated web queries",
        component="services.url_fetcher",
        hunt_id=hunt_id,
        result_summary={"query_count": len(queries), "queries": [_truncate(q, QUERY_PREVIEW_MAX_CHARS) for q in queries]},
    )

    results: List[Dict[str, Any]] = []

    for index, query in enumerate(queries):
        query_fp = _query_fingerprint(query)
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.started",
            status="started",
            message="Searching web for query",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
        )
        try:
            search_results = _search_web_via_searxng(
                query=query,
                max_results=10,
                hunt_id=hunt_id,
            )
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="SearXNG web search failed",
                component="services.url_fetcher",
                provider="searxng",
                operation="search",
                hunt_id=hunt_id,
                query_fingerprint=query_fp,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"SearxNG web search failed for query fingerprint '{query_fp}': {str(e)}") from e

        urls = _extract_search_results(search_results)
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="SearXNG web search completed",
            component="services.url_fetcher",
            provider="searxng",
            operation="search",
            hunt_id=hunt_id,
            query_fingerprint=query_fp,
            result_summary={
                "query": _truncate(query, QUERY_PREVIEW_MAX_CHARS),
                "url_count": len(urls),
                "urls_preview": [
                    {
                        "title": _truncate(str(url.get("title", "")), QUERY_PREVIEW_MAX_CHARS),
                        "url": _truncate(str(url.get("url", "")), URL_PREVIEW_MAX_CHARS),
                    }
                    for url in urls[:RESULTS_PREVIEW_URLS_PER_QUERY]
                    if isinstance(url, dict)
                ],
            },
        )
        results.append({"query": query, "urls": urls})

        if index < len(queries) - 1:
            log_event(
                logger,
                level=logging.INFO,
                event="task.retrying",
                status="retrying",
                message="Waiting before next web search query",
                component="services.url_fetcher",
                hunt_id=hunt_id,
                delay_seconds=INTER_QUERY_DELAY_SECONDS,
            )
            await asyncio.sleep(INTER_QUERY_DELAY_SECONDS)

    total_urls = sum(
        len(result.get("urls", []))
        for result in results
        if isinstance(result, dict) and isinstance(result.get("urls", []), list)
    )
    unique_urls = len(
        {
            str(url.get("url", "")).strip()
            for result in results
            if isinstance(result, dict) and isinstance(result.get("urls", []), list)
            for url in result.get("urls", [])
            if isinstance(url, dict) and str(url.get("url", "")).strip()
        }
    )
    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="URL fetcher completed all query searches",
        component="services.url_fetcher",
        hunt_id=hunt_id,
        result_summary={
            "query_count": len(results),
            "total_url_count": total_urls,
            "unique_url_count": unique_urls,
            "results_preview": _build_results_preview(results),
        },
    )

    return results
