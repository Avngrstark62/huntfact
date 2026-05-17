from typing import Any, Dict, List, Literal

from pydantic import BaseModel

from chroma_client import chroma_client
from config import settings
from llm import llm
from logging_config import get_logger
from services.embeddings.embeddings import get_embeddings

logger = get_logger("services.claim_verifier.claim_verifier")

ALLOWED_VERDICTS = {"true", "false", "partially true", "no verdict"}
MAX_QUERIES = 6
MAX_CHUNKS_PER_QUERY = 5
MAX_DISTANCE = 0.35


class ClaimVerificationRow(BaseModel):
    claim: str
    verdict: Literal["true", "false", "partially true", "no verdict"]
    sources: List[str]
    explanation: str


class ClaimVerificationResponse(BaseModel):
    rows: List[ClaimVerificationRow]


class RetrievalQueriesResponse(BaseModel):
    queries: List[str]


def _normalize_claims(claims: List[str]) -> List[str]:
    cleaned_claims: List[str] = []
    for claim in claims:
        if not isinstance(claim, str):
            continue
        value = claim.strip()
        if value:
            cleaned_claims.append(value)
    return cleaned_claims


def _normalize_queries(queries: List[str]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for query in queries:
        if not isinstance(query, str):
            continue
        value = query.strip()
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        normalized.append(value)
        if len(normalized) >= MAX_QUERIES:
            break
    return normalized


def _format_context_for_llm(sources: List[Dict[str, Any]]) -> str:
    chunks: List[str] = []
    for index, source in enumerate(sources, 1):
        chunks.append(
            "\n".join(
                [
                    f"Source {index}",
                    f"URL: {source['url']}",
                    f"Title: {source.get('title', '')}",
                    f"Retrieval query: {source.get('retrieval_query', '')}",
                    f"Distance: {source.get('distance')}",
                    "Content:",
                    source["content"],
                ]
            )
        )
    return "\n\n---\n\n".join(chunks)


async def _generate_retrieval_queries(claims: List[str]) -> List[str]:
    claims_text = "\n".join([f"- {claim}" for claim in claims])
    prompt = f"""You are preparing retrieval queries for claim verification.

Claims:
{claims_text}

Task:
- Return a minimal set of web-search-style queries that can verify all claims.
- Keep queries specific and evidence-focused.
- Avoid redundant or overlapping queries.
- Return between 1 and {MAX_QUERIES} queries.
"""
    messages = [
        {
            "role": "system",
            "content": "Generate concise retrieval queries to verify factual claims.",
        },
        {"role": "user", "content": prompt},
    ]

    result = await llm.call_with_schema(
        model=settings.reasoning_model,
        messages=messages,
        schema_model=RetrievalQueriesResponse,
    )
    queries = _normalize_queries(result.queries)
    if queries:
        return queries
    return claims


def _extract_chunks_for_query(
    collection: Any,
    query: str,
    query_embedding: List[float],
) -> List[Dict[str, Any]]:
    query_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=MAX_CHUNKS_PER_QUERY,
        include=["documents", "metadatas", "distances"],
    )

    documents = (query_result.get("documents") or [[]])[0]
    metadatas = (query_result.get("metadatas") or [[]])[0]
    distances = (query_result.get("distances") or [[]])[0]
    matched_chunks: List[Dict[str, Any]] = []

    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        if distance is None or float(distance) > MAX_DISTANCE:
            continue

        url = str((metadata or {}).get("source_url") or (metadata or {}).get("url") or "").strip()
        content = str(document or "").strip()
        if not url or not content:
            continue

        matched_chunks.append(
            {
                "url": url,
                "title": str((metadata or {}).get("source_title") or (metadata or {}).get("title") or "").strip(),
                "query": str((metadata or {}).get("source_query") or (metadata or {}).get("query") or "").strip(),
                "retrieval_query": query,
                "distance": float(distance),
                "content": content,
            }
        )

    return matched_chunks


def _dedupe_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        key = (chunk["url"], chunk["content"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


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


async def verify_claims_with_context(claims: List[str], rag_collection_name: str) -> Dict[str, Any]:
    normalized_claims = _normalize_claims(claims)
    if not normalized_claims:
        logger.warning("No valid claims provided to claim verifier")
        return {"rows": []}

    if not isinstance(rag_collection_name, str) or not rag_collection_name.strip():
        logger.warning("No valid rag collection name provided to claim verifier")
        return {
            "rows": [
                {
                    "claim": claim,
                    "verdict": "no verdict",
                    "sources": [],
                    "explanation": "No valid RAG collection was provided for verification.",
                }
                for claim in normalized_claims
            ]
        }

    retrieval_queries = await _generate_retrieval_queries(normalized_claims)
    logger.info(
        "Generated %s retrieval queries for %s claims",
        len(retrieval_queries),
        len(normalized_claims),
    )

    chroma = chroma_client.connect()
    collection = chroma.get_collection(name=rag_collection_name.strip())

    all_chunks: List[Dict[str, Any]] = []
    for retrieval_query in retrieval_queries:
        query_embedding = get_embeddings([retrieval_query])[0]
        all_chunks.extend(_extract_chunks_for_query(collection, retrieval_query, query_embedding))

    context_sources = _dedupe_chunks(all_chunks)
    if not context_sources:
        logger.warning("No RAG chunks matched distance threshold for claim verifier")
        return {
            "rows": [
                {
                    "claim": claim,
                    "verdict": "no verdict",
                    "sources": [],
                    "explanation": "No relevant retrieved evidence was found for this claim cluster.",
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
        "Generating claim verification for %s claims using %s retrieved chunks from collection %s",
        len(normalized_claims),
        len(context_sources),
        rag_collection_name.strip(),
    )
    result = await llm.call_with_schema(
        model=settings.reasoning_model,
        messages=messages,
        schema_model=ClaimVerificationResponse,
    )

    allowed_urls = {source["url"] for source in context_sources}
    rows = _normalize_rows(normalized_claims, result.rows, allowed_urls)
    return {"rows": rows}
