from typing import Any, Dict
import logging

from pydantic import BaseModel

from config import settings
from db.database import db
from llm import llm
from logging_config import get_logger, log_event
from result_schema import FactCheckResult, FactCheckRow

logger = get_logger("services.save_result_to_db.save_result_to_db")


class HuntMetadataResponse(BaseModel):
    title: str
    summary: str


def _extract_rows(table: Dict[str, Any]) -> list[FactCheckRow]:
    rows = table.get("rows")
    if not isinstance(rows, list):
        return []
    return FactCheckResult.model_validate(rows).root


def _compute_trust_score(rows: list[FactCheckRow]) -> int:
    if not rows:
        return 0

    return round(sum(row.confidence for row in rows) / len(rows))


def _build_reel_recall_title(rows: list[FactCheckRow]) -> str:
    for row in rows:
        words = row.claim.split()
        if words:
            return " ".join(words[:10]).strip()
    return "Reel fact check"


async def _generate_hunt_metadata(rows: list[FactCheckRow]) -> tuple[str, str]:
    if not rows:
        return "Fact-check result unavailable", "No verifiable claims were available in this run."

    verdict_counts: dict[str, int] = {}
    for row in rows:
        verdict = row.verdict
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    top_verdict = max(verdict_counts.items(), key=lambda item: item[1])[0]
    fallback_title = _build_reel_recall_title(rows)
    fallback_summary = (
        "This reel appears to center on factual assertions summarized in the extracted claims. "
        f"Overall credibility is mixed, with {top_verdict} being the most common assessment."
    )

    row_summaries: list[str] = []
    for index, row in enumerate(rows, 1):
        row_summaries.append(
            "\n".join(
                [
                    f"Claim {index}: {row.claim}",
                    f"Verdict: {row.verdict}",
                    f"Confidence: {row.confidence}",
                    f"Explanation: {row.explanation}",
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
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.started",
            status="started",
            message="Generating hunt metadata with LLM",
            component="services.save_result_to_db",
            provider="openai",
            operation="generate_hunt_metadata",
            result_summary={"row_count": len(rows)},
        )
        result = await llm.call_with_schema(
            model=settings.llm.reasoning_model,
            messages=messages,
            schema_model=HuntMetadataResponse,
        )
        title = result.title.strip() or fallback_title
        summary = result.summary.strip() or fallback_summary
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="Generated hunt metadata with LLM",
            component="services.save_result_to_db",
            provider="openai",
            operation="generate_hunt_metadata",
        )
        return title, summary
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Failed to generate hunt metadata",
            component="services.save_result_to_db",
            provider="openai",
            operation="generate_hunt_metadata",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        return fallback_title, fallback_summary


async def save_result_to_db(hunt_id: int, table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist claim verifier rows in hunts.result as JSON.

    Args:
        hunt_id: Target hunt id.
        table: Structured claim-verifier result table.

    Returns:
        Dict with save metadata.
    """
    rows = _extract_rows(table)
    if not rows:
        raise ValueError("Result rows are missing or invalid")
    log_event(
        logger,
        level=logging.INFO,
        event="db.write.started",
        status="started",
        message="Saving result table to DB",
        component="services.save_result_to_db",
        hunt_id=hunt_id,
        result_summary={"row_count": len(rows)},
    )

    title, summary = await _generate_hunt_metadata(rows)
    trust_score = _compute_trust_score(rows)
    row_dicts = [row.model_dump() for row in rows]
    session = db.SessionLocal()

    try:
        updated_hunt = db.update_hunt_result(
            session=session,
            hunt_id=hunt_id,
            result=row_dicts,
            title=title,
            summary=summary,
            trust_score=trust_score,
        )
        if not updated_hunt:
            raise RuntimeError(f"Hunt not found for hunt_id={hunt_id}")

        log_event(
            logger,
            level=logging.INFO,
            event="db.write.succeeded",
            status="succeeded",
            message="Saved result table to DB",
            component="services.save_result_to_db",
            hunt_id=hunt_id,
            result_summary={"row_count": len(row_dicts)},
        )
        return {
            "hunt_id": hunt_id,
            "result": row_dicts,
            "title": updated_hunt.title,
            "summary": updated_hunt.summary,
            "trust_score": updated_hunt.trust_score,
        }
    finally:
        session.close()
