from typing import Any, Dict, List

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger
from services.firecrawl.firecrawl import fetch_markdown_with_firecrawl

logger = get_logger("services.web_scraper.web_scraper")


class SelectedUrlsResponse(BaseModel):
    selected_indices: List[int]


def _normalize_claims(claims: List[str]) -> List[str]:
    cleaned_claims: List[str] = []
    for claim in claims:
        if not isinstance(claim, str):
            continue
        value = claim.strip()
        if value:
            cleaned_claims.append(value)
    return cleaned_claims


def _extract_candidates(url_fetcher_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    for result in url_fetcher_results:
        if not isinstance(result, dict):
            continue

        query = str(result.get("query", "")).strip()
        urls = result.get("urls", [])
        if not isinstance(urls, list):
            continue

        for url_entry in urls:
            if not isinstance(url_entry, dict):
                continue

            raw_url = url_entry.get("url") or url_entry.get("href") or ""
            cleaned_url = str(raw_url).strip()
            if not cleaned_url:
                continue

            candidates.append(
                {
                    "query": query,
                    "title": str(url_entry.get("title", "")).strip(),
                    "url": cleaned_url,
                }
            )
    return candidates


def _format_candidates_for_llm(candidates: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, candidate in enumerate(candidates):
        lines.append(
            f"[{idx}] Query: {candidate['query']} | Title: {candidate['title']} | URL: {candidate['url']}"
        )
    return "\n".join(lines)


def _normalize_selected_indices(selected_indices: List[int], total_candidates: int) -> List[int]:
    normalized: List[int] = []
    seen: set[int] = set()

    for idx in selected_indices:
        if not isinstance(idx, int):
            continue
        if idx < 0 or idx >= total_candidates:
            continue
        if idx in seen:
            continue

        seen.add(idx)
        normalized.append(idx)

        if len(normalized) == 5:
            break

    return normalized


async def _select_urls_with_llm(
    claims: List[str], candidates: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    claims_text = "\n".join([f"- {claim}" for claim in claims])
    candidates_text = _format_candidates_for_llm(candidates)

    prompt = f"""You are selecting web sources for fact verification.

Claims to verify:
{claims_text}

Candidate URLs:
{candidates_text}

Task:
- Select URLs that are useful to verify the claims.
- Evaluate all candidate URLs as one combined pool.
- You may select zero URLs if none are useful.
- If you select URLs, select at most 5.
- Return only the selected candidate indices.
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a fact-checking research assistant. "
                "Select only URLs that are relevant and credible for claim verification."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    result = await llm.call_with_schema(
        model=settings.llm.reasoning_model,
        messages=messages,
        schema_model=SelectedUrlsResponse,
    )

    selected_indices = _normalize_selected_indices(result.selected_indices, len(candidates))
    return [candidates[idx] for idx in selected_indices]


def _build_context(scraped_sources: List[Dict[str, str]]) -> Dict[str, Any]:
    if not scraped_sources:
        return {"sources": []}

    sources: List[Dict[str, Any]] = []
    for index, source in enumerate(scraped_sources, 1):
        sources.append(
            {
                "source_id": index,
                "url": source["url"],
                "title": source["title"],
                "query": source["query"],
                "content": source["markdown"],
            }
        )

    return {"sources": sources}


async def build_web_verification_context(
    claims: List[str], url_fetcher_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build a merged markdown context from LLM-selected URLs.

    Args:
        claims: Objective factual claims.
        url_fetcher_results: URL fetcher output results list.

    Returns:
        Merged markdown context for downstream citation and verification.
    """
    normalized_claims = _normalize_claims(claims)
    if not normalized_claims:
        logger.warning("No valid claims received for web scraping")
        return {"sources": []}

    candidates = _extract_candidates(url_fetcher_results)
    if not candidates:
        logger.warning("No valid URL candidates received for web scraping")
        return {"sources": []}

    logger.info(
        f"Selecting verification URLs from {len(candidates)} candidates for {len(normalized_claims)} claims"
    )
    selected_candidates = await _select_urls_with_llm(normalized_claims, candidates)

    if not selected_candidates:
        logger.info("LLM selected no URLs for verification context")
        return {"sources": []}

    scraped_sources: List[Dict[str, str]] = []
    for candidate in selected_candidates:
        url = candidate["url"]
        try:
            markdown = fetch_markdown_with_firecrawl(url)
        except Exception as e:
            logger.error(f"Failed to scrape URL '{url}' with Firecrawl: {str(e)}", exc_info=True)
            continue

        scraped_sources.append(
            {
                "url": url,
                "title": candidate["title"],
                "query": candidate["query"],
                "markdown": markdown.strip(),
            }
        )

    context = _build_context(scraped_sources)
    logger.info(
        f"Built web verification context from {len(scraped_sources)} scraped sources"
    )
    return context
