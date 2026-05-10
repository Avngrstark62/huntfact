from typing import List

from pydantic import BaseModel

from config import settings
from llm import llm
from logging_config import get_logger

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
        logger.warning("No content to extract claim clusters from")
        return []

    logger.info(f"Extracting claim clusters from content ({len(content)} chars)")

    prompt = f"""Extract objective factual claims from the content and group them into clusters for web verification.

Definitions:
1. Claim:
- A factual, objective statement that can be verified as true or false.
- Must be standalone and independent.
- Avoid references like "it", "they", "this" when antecedent is outside the claim.
- Keep each claim self-contained.
- Must be directly stated in the content.
- Include full identifying context so the claim is meaningful alone (who/what/where/when as needed).

2. Cluster:
- A list of claims that can all be verified with one web search.
- If two claims require different web searches to verify, they must be in different clusters.
- Similar wording does not matter; verification search intent is what matters.

Output requirements:
- Return only objective factual claims about publicly verifiable real-world topics.
- Focus on claims about public events, public institutions, public policy, history, science, economics, sports, or notable public figures/entities.
- Exclude opinions, predictions, and normative statements.
- Exclude personal anecdotes, creator-specific personal incidents, private disputes, threats, self-promotion, marketing copy, and "my channel/my class/my followers" style claims.
- Exclude claims about niche social-media drama or claims that cannot be independently verified through broadly available web sources.
- Keep claims concise and precise.
- Group all extracted claims into one or more clusters.
- Do not invent, infer, or add background facts that are not explicitly asserted in the content.
- If the content has no objective factual claims, return an empty clusters list.
- If a claim depends on missing context from another sentence, rewrite it to be fully standalone; if that is not possible, discard it.

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
            model=settings.reasoning_model,
            messages=messages,
            schema_model=ClaimClustersResponse,
        )
        normalized_clusters = _normalize_clusters(result.clusters)
        logger.info(f"Successfully extracted {len(normalized_clusters)} claim clusters")
        return normalized_clusters
    except Exception as e:
        logger.error(f"Failed to extract claim clusters: {str(e)}", exc_info=True)
        raise
