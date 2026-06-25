import json
from typing import Any, Dict

from pydantic import BaseModel

from config import settings
from db.database import db
from llm import llm
from logging_config import get_logger

logger = get_logger("services.save_result_to_db.save_result_to_db")


class HuntMetadataResponse(BaseModel):
    title: str
    summary: str


def _extract_rows(table: Dict[str, Any]) -> list[Dict[str, Any]]:
    rows = table.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _compute_trust_score(table: Dict[str, Any]) -> int:
    confidences: list[int] = []
    for row in _extract_rows(table):
        raw_confidence = row.get("confidence")
        try:
            confidence = int(raw_confidence)
        except (TypeError, ValueError):
            continue
        confidences.append(max(0, min(100, confidence)))

    if not confidences:
        return 0

    return round(sum(confidences) / len(confidences))


def _build_reel_recall_title(rows: list[Dict[str, Any]]) -> str:
    for row in rows:
        claim = str(row.get("claim", "")).strip()
        if claim:
            words = claim.split()
            return " ".join(words[:10]).strip()
    return "Reel fact check"


async def _generate_hunt_metadata(table: Dict[str, Any]) -> tuple[str, str]:
    rows = _extract_rows(table)
    if not rows:
        return "Fact-check result unavailable", "No verifiable claims were available in this run."

    verdict_counts: dict[str, int] = {}
    for row in rows:
        verdict = str(row.get("verdict", "unverified")).strip().lower() or "unverified"
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    top_verdict = max(verdict_counts.items(), key=lambda item: item[1])[0]
    fallback_title = _build_reel_recall_title(rows)
    fallback_summary = (
        "This reel appears to center on factual assertions summarized in the extracted claims. "
        f"Overall credibility is mixed, with {top_verdict} being the most common assessment."
    )

    row_summaries: list[str] = []
    for index, row in enumerate(rows, 1):
        claim = str(row.get("claim", "")).strip()
        verdict = str(row.get("verdict", "")).strip()
        confidence = row.get("confidence")
        explanation = str(row.get("explanation", "")).strip()
        row_summaries.append(
            "\n".join(
                [
                    f"Claim {index}: {claim}",
                    f"Verdict: {verdict}",
                    f"Confidence: {confidence}",
                    f"Explanation: {explanation}",
                ]
            )
        )

    prompt = f"""You are generating user-facing metadata for a fact-checking result.

Input:
{chr(10).join(row_summaries)}

Task:
- Generate a brief title that helps the user instantly remember which reel this is.
- Generate a short summary (2-3 sentences) that first explains the reel's overall purpose/message, then assesses its credibility.

Requirements:
- Keep the title under 10 words.
- The title should sound like a memory cue for the reel topic, not a verdict headline.
- Avoid generic titles like "Fact Check Result" or "Verification Complete".
- Keep the summary under 90 words.
- Use plain, neutral language.
- In the summary, describe the reel's main intent before discussing credibility.
- Do not make the title or summary purely a list of claim verdicts.
- Do not include markdown, bullet points, or quotes.
- Do not mention internal pipeline terms.
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You create concise, accurate user-facing metadata for reel fact checks. "
                "Write titles as reel-memory cues and summaries as reel-purpose plus credibility assessment."
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
            schema_model=HuntMetadataResponse,
        )
        title = result.title.strip() or fallback_title
        summary = result.summary.strip() or fallback_summary
        return title, summary
    except Exception as e:
        logger.error("Failed to generate hunt metadata: %s", str(e), exc_info=True)
        return fallback_title, fallback_summary


async def save_result_to_db(hunt_id: int, table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist claim verifier table in hunts.result as a JSON string.

    Args:
        hunt_id: Target hunt id.
        table: Structured claim-verifier result table.

    Returns:
        Dict with save metadata.
    """
    serialized_result = json.dumps(table, ensure_ascii=False)
    title, summary = await _generate_hunt_metadata(table)
    trust_score = _compute_trust_score(table)
    session = db.SessionLocal()

    try:
        updated_hunt = db.update_hunt_result(
            session=session,
            hunt_id=hunt_id,
            result=serialized_result,
            title=title,
            summary=summary,
            trust_score=trust_score,
        )
        if not updated_hunt:
            raise RuntimeError(f"Hunt not found for hunt_id={hunt_id}")

        logger.info(f"Saved result table to DB for hunt_id: {hunt_id}")
        return {
            "hunt_id": hunt_id,
            "result": serialized_result,
            "title": updated_hunt.title,
            "summary": updated_hunt.summary,
            "trust_score": updated_hunt.trust_score,
        }
    finally:
        session.close()
