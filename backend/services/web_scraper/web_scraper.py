from typing import Any, Dict, List
import logging

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger, log_event, sanitize_url
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

        if len(normalized) == 10:
            break

    return normalized


async def _select_urls_with_llm(
    claims: List[str], candidates: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    claims_text = "\n".join([f"- {claim}" for claim in claims])
    candidates_text = _format_candidates_for_llm(candidates)

#     prompt = f"""You are selecting web sources for fact verification.
#
# Claims to verify:
# {claims_text}
#
# Candidate URLs:
# {candidates_text}
#
# Task:
# - Select URLs that are useful to verify the claims.
# - Evaluate all candidate URLs as one combined pool.
# - You may select zero URLs if none are useful.
# - If you select URLs, select at most 5.
# - Return only the selected candidate indices.
# """
#
#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a fact-checking research assistant. "
#                 "Select only URLs that are relevant and credible for claim verification."
#             ),
#         },
#         {
#             "role": "user",
#             "content": prompt,
#         },
#     ]
#
    prompt = f"""You are selecting web sources for factual claim verification.

Claims to verify:
{claims_text}

Candidate URLs:
{candidates_text}

Task:
Select the minimum set of URLs that collectively provides sufficient evidence to verify all claims.

Algorithm:
1. Treat all candidate URLs as one combined pool.
2. Initially consider every claim uncovered.
3. For each URL, estimate:
   - which claims it provides direct evidence for,
   - how complete that evidence is,
   - and how authoritative and trustworthy the source appears.
4. Select the URL that contributes the greatest amount of useful evidence for currently uncovered claims.
5. Mark sufficiently covered claims as covered.
6. Repeat until every claim has sufficient evidence or no remaining URL provides meaningful additional evidence.
7. If multiple URLs provide substantially the same evidence, keep only the one with the stronger evidence and higher source authority.
8. Select lower-authority sources only when they contribute meaningful evidence that is not available from stronger sources.

Requirements:
- Select only URLs that materially improve the available evidence.
- Select zero URLs if none are useful.
- Do not select redundant URLs.
- Return only the selected candidate indices.
"""

    messages = [
    {
        "role": "system",
        "content": (
            "You are a fact-checking research assistant. "
            "Your objective is to maximize the quality and completeness of the evidence available to a downstream verifier while minimizing redundant sources. "
            "Follow the provided algorithm exactly. "
            "Return only the requested structured output."
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
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="skipped",
            message="No valid claims received for web scraping",
            component="services.web_scraper",
        )
        return {"sources": []}

    candidates = _extract_candidates(url_fetcher_results)
    if not candidates:
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="skipped",
            message="No valid URL candidates received",
            component="services.web_scraper",
        )
        return {"sources": []}

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Selecting verification URLs with LLM",
        component="services.web_scraper",
        provider="openai",
        operation="select_urls",
        result_summary={"candidate_count": len(candidates), "claim_count": len(normalized_claims)},
    )
    selected_candidates = await _select_urls_with_llm(normalized_claims, candidates)

    if not selected_candidates:
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="skipped",
            message="LLM selected no URLs for verification context",
            component="services.web_scraper",
            provider="openai",
            operation="select_urls",
        )
        return {"sources": []}

    scraped_sources: List[Dict[str, str]] = []
    for candidate in selected_candidates:
        url = candidate["url"]
        try:
            markdown = fetch_markdown_with_firecrawl(url)
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="Failed to scrape selected URL",
                component="services.web_scraper",
                provider="firecrawl",
                operation="scrape",
                url=sanitize_url(url),
                error_type=type(e).__name__,
                error_message=str(e),
            )
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
    log_event(
        logger,
        level=logging.INFO,
        event="task.succeeded",
        status="succeeded",
        message="Built web verification context",
        component="services.web_scraper",
        result_summary={"scraped_source_count": len(scraped_sources)},
    )
    return context
