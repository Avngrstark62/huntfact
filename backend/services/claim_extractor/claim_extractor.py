from typing import List
import logging

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger, log_event

logger = get_logger("services.claim_extractor.claim_extractor")


class ClaimCluster(BaseModel):
    claims: List[str]


class ClaimClustersResponse(BaseModel):
    clusters: List[ClaimCluster]


def _normalize_clusters(clusters: List[ClaimCluster]) -> List[List[str]]:
    normalized_clusters: List[List[str]] = []

    for cluster in clusters:
        cleaned_claims: List[str] = []
        seen_claims: set[str] = set()

        for claim in cluster.claims:
            normalized_claim = claim.strip()
            if not normalized_claim:
                continue
            if normalized_claim in seen_claims:
                continue

            seen_claims.add(normalized_claim)
            cleaned_claims.append(normalized_claim)

        if cleaned_claims:
            normalized_clusters.append(cleaned_claims)

    return normalized_clusters


async def extract_claim_clusters(content: str) -> List[List[str]]:
    """
    Extract clusters of objective claims from content.

    Args:
        content: Raw text content to analyze

    Returns:
        List of claim clusters, where each cluster is a list of standalone claims
    """
    if not content:
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="skipped",
            message="No content to extract claim clusters from",
            component="services.claim_extractor",
        )
        return []

    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.started",
        status="started",
        message="Extracting claim clusters",
        component="services.claim_extractor",
        provider="openai",
        operation="claim_cluster_extract",
        result_summary={"content_chars": len(content)},
    )

    prompt = f"""Extract objective factual claims from the content and group them into verification clusters.

Definitions:

1. Claim
- A claim is a standalone real-world assertion that can be independently verified.
- Extract the underlying factual meaning, not the exact wording.
- Preserve the core asserted event/state/relation, not decorative or rhetorical details.
- Remove incidental details that are not essential for verification.
- Keep the minimal sufficient context needed for verification.
- Resolve references and missing context so the claim is fully standalone.
- Include explicit entities, subjects, locations, and time context when required.
- Do not split dependent context across separate claims.
- Do not invent or infer facts not asserted in the content.

2. Cluster
- A cluster contains claims that can be verified using the same search intent and evidence set.
- Claims requiring different evidence or search intent must be separated.

Extraction Rules:
- Focus only on objective, publicly verifiable claims.
- Exclude opinions, predictions, speculation, rhetoric, emotional framing, and normative statements.
- Exclude private/personal incidents that cannot be broadly verified.
- Prefer semantically canonical claims optimized for verification and retrieval.
- Avoid overly literal extraction.
- Avoid over-specific wording that may cause verification failure.
- Avoid vague or underspecified claims.
- Each claim must represent one atomic verifiable assertion.
- Keep claims concise but semantically complete.
- If no valid factual claims exist, return an empty clusters list.

Content:
{content}
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You extract objective factual claims and cluster them by "
                "single-search verifiability. You must stay grounded in the "
                "provided content only. Never hallucinate or introduce outside facts. "
                "Only keep publicly verifiable real-world claims, not personal or creator-specific incidents. "
                "Every claim must be self-contained and meaningful on its own. "
                "If no objective factual claims are present, return empty clusters."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    try:
        result = await llm.call_with_schema(
            model=settings.llm.reasoning_model,
            messages=messages,
            schema_model=ClaimClustersResponse,
        )
        normalized_clusters = _normalize_clusters(result.clusters)
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="Extracted claim clusters",
            component="services.claim_extractor",
            provider="openai",
            operation="claim_cluster_extract",
            result_summary={"cluster_count": len(normalized_clusters)},
        )
        return normalized_clusters
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Failed to extract claim clusters",
            component="services.claim_extractor",
            provider="openai",
            operation="claim_cluster_extract",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        raise
