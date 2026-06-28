"""store hunt result as json

Revision ID: e2b7c4a9d1f0
Revises: d4e7f21c8a9b
Create Date: 2026-06-28 08:02:00.000000

"""
from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2b7c4a9d1f0"
down_revision: Union[str, None] = "d4e7f21c8a9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_result_value(raw_value: str | None) -> list[dict]:
    allowed_verdicts = {
        "true",
        "mostly true",
        "unverified",
        "mostly false",
        "false",
    }

    def normalize_row(row: object) -> dict | None:
        if not isinstance(row, dict):
            return None

        claim = str(row.get("claim") or "").strip()
        if not claim:
            return None

        verdict = str(row.get("verdict") or "unverified").strip().lower()
        if verdict == "no verdict":
            verdict = "unverified"
        if verdict not in allowed_verdicts:
            verdict = "unverified"

        raw_confidence = row.get("confidence", 50)
        try:
            confidence = int(raw_confidence)
        except Exception:
            confidence = 50
        confidence = max(0, min(100, confidence))

        raw_sources = row.get("sources")
        if isinstance(raw_sources, list):
            sources = [str(item).strip() for item in raw_sources if str(item).strip()]
        else:
            sources = []

        explanation = str(row.get("explanation") or "").strip()
        if not explanation:
            explanation = "No explanation provided."

        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "sources": sources,
            "explanation": explanation,
        }

    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return []

    if isinstance(parsed, list):
        normalized_rows: list[dict] = []
        for row in parsed:
            normalized = normalize_row(row)
            if normalized is not None:
                normalized_rows.append(normalized)
        return normalized_rows

    if isinstance(parsed, dict):
        rows = parsed.get("rows")
        if isinstance(rows, list):
            normalized_rows: list[dict] = []
            for row in rows:
                normalized = normalize_row(row)
                if normalized is not None:
                    normalized_rows.append(normalized)
            return normalized_rows

    return []


def upgrade() -> None:
    bind = op.get_bind()
    hunts_table = sa.table(
        "hunts",
        sa.column("id", sa.Integer()),
        sa.column("result_json", sa.JSON()),
    )

    with op.batch_alter_table("hunts") as batch_op:
        batch_op.add_column(sa.Column("result_json", sa.JSON(), nullable=True))

    rows = bind.execute(sa.text("SELECT id, result FROM hunts")).mappings().all()
    for row in rows:
        normalized_rows = _normalize_result_value(row.get("result"))
        bind.execute(
            hunts_table.update()
            .where(hunts_table.c.id == row["id"])
            .values(result_json=normalized_rows)
        )

    with op.batch_alter_table("hunts") as batch_op:
        batch_op.drop_column("result")
        batch_op.alter_column("result_json", new_column_name="result")


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("hunts") as batch_op:
        batch_op.add_column(sa.Column("result_text", sa.String(), nullable=True))

    rows = bind.execute(sa.text("SELECT id, result FROM hunts")).mappings().all()
    for row in rows:
        raw_value = row.get("result")
        result_text = "[]"
        if raw_value is not None:
            result_text = json.dumps(raw_value)
        bind.execute(
            sa.text("UPDATE hunts SET result_text = :result_text WHERE id = :id"),
            {"id": row["id"], "result_text": result_text},
        )

    with op.batch_alter_table("hunts") as batch_op:
        batch_op.drop_column("result")
        batch_op.alter_column("result_text", new_column_name="result")
