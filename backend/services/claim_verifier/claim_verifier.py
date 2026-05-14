from typing import Any, Dict, List, Literal

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger

logger = get_logger("services.claim_verifier.claim_verifier")

ALLOWED_VERDICTS = {"true", "false", "partially true", "no verdict"}


class ClaimVerificationRow(BaseModel):
    claim: str
    verdict: Literal["true", "false", "partially true", "no verdict"]
    sources: List[str]
    explanation: str


class ClaimVerificationResponse(BaseModel):
    rows: List[ClaimVerificationRow]


def _normalize_claims(claims: List[str]) -> List[str]:
    cleaned_claims: List[str] = []
    for claim in claims:
        if not isinstance(claim, str):
            continue
        value = claim.strip()
        if value:
            cleaned_claims.append(value)
    return cleaned_claims


def _extract_context_sources(context: Dict[str, Any]) -> List[Dict[str, str]]:
    raw_sources = context.get("sources", [])
    if not isinstance(raw_sources, list):
        return []

    sources: List[Dict[str, str]] = []
    for source in raw_sources:
        if not isinstance(source, dict):
            continue

        url = str(source.get("url", "")).strip()
        content = str(source.get("content", "")).strip()
        if not url or not content:
            continue

        sources.append(
            {
                "url": url,
                "title": str(source.get("title", "")).strip(),
                "query": str(source.get("query", "")).strip(),
                "content": content,
            }
        )

    return sources


def _format_context_for_llm(sources: List[Dict[str, str]]) -> str:
    chunks: List[str] = []
    for index, source in enumerate(sources, 1):
        chunks.append(
            "\n".join(
                [
                    f"Source {index}",
                    f"URL: {source['url']}",
                    f"Title: {source['title']}",
                    f"Query: {source['query']}",
                    "Content:",
                    source["content"],
                ]
            )
        )
    return "\n\n---\n\n".join(chunks)


def _claim_key(claim: str) -> str:
    return claim.strip().lower()


def _normalize_rows(
    claims: List[str], rows: List[ClaimVerificationRow], allowed_urls: set[str]
) -> List[Dict[str, Any]]:
    row_by_claim: Dict[str, ClaimVerificationRow] = {}
    for row in rows:
        key = _claim_key(row.claim)
        if key and key not in row_by_claim:
            row_by_claim[key] = row

    normalized_rows: List[Dict[str, Any]] = []
    for claim in claims:
        matched = row_by_claim.get(_claim_key(claim))
        if not matched:
            normalized_rows.append(
                {
                    "claim": claim,
                    "verdict": "no verdict",
                    "sources": [],
                    "explanation": "No claim-specific verdict could be generated from the provided context.",
                }
            )
            continue

        verdict = matched.verdict if matched.verdict in ALLOWED_VERDICTS else "no verdict"
        sources = [url for url in matched.sources if isinstance(url, str) and url in allowed_urls]
        explanation = matched.explanation.strip()
        if not explanation:
            explanation = "No explanation was provided for this claim."

        normalized_rows.append(
            {
                "claim": claim,
                "verdict": verdict,
                "sources": sources,
                "explanation": explanation,
            }
        )

    return normalized_rows


async def verify_claims_with_context(claims: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
    normalized_claims = _normalize_claims(claims)
    if not normalized_claims:
        logger.warning("No valid claims provided to claim verifier")
        return {"rows": []}

    context_sources = _extract_context_sources(context)
    if not context_sources:
        logger.warning("No valid context sources provided to claim verifier")
        return {
            "rows": [
                {
                    "claim": claim,
                    "verdict": "no verdict",
                    "sources": [],
                    "explanation": "No usable context sources were provided for verification.",
                }
                for claim in normalized_claims
            ]
        }

    claims_text = "\n".join([f"- {claim}" for claim in normalized_claims])
    context_text = _format_context_for_llm(context_sources)

    prompt = f"""You are a strict factual claim verifier.

Claims:
{claims_text}

Context sources:
{context_text}

Rules:
- Use only the provided context sources.
- Do not use prior knowledge, assumptions, or common sense outside the given context.
- Return one row for every claim.
- Keep claim text exactly as provided.
- Verdict must be one of: true, false, partially true, no verdict.
- Include only URLs from the provided context that are directly used for that specific claim.
- Explanation must be 50-300 words, detailed but non-redundant.
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You verify claims strictly from provided evidence. "
                "If evidence is insufficient or conflicting, use 'no verdict'."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    logger.info(
        f"Generating claim verification for {len(normalized_claims)} claims using {len(context_sources)} context sources"
    )
    result = await llm.call_with_schema(
        model=settings.reasoning_model,
        messages=messages,
        schema_model=ClaimVerificationResponse,
    )

    allowed_urls = {source["url"] for source in context_sources}
    rows = _normalize_rows(normalized_claims, result.rows, allowed_urls)
    return {"rows": rows}
