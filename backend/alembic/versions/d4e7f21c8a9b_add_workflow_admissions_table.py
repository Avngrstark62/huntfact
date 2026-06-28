"""add workflow admissions table

Revision ID: d4e7f21c8a9b
Revises: 9c12a4d6e8f1
Create Date: 2026-06-27 14:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e7f21c8a9b"
down_revision: Union[str, None] = "9c12a4d6e8f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_admissions",
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("video_link", sa.String(), nullable=False),
        sa.Column("hunt_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id"),
    )
    op.create_index(
        op.f("ix_workflow_admissions_workflow_id"),
        "workflow_admissions",
        ["workflow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_admissions_video_link"),
        "workflow_admissions",
        ["video_link"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_admissions_hunt_id"),
        "workflow_admissions",
        ["hunt_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_admissions_hunt_id"), table_name="workflow_admissions")
    op.drop_index(op.f("ix_workflow_admissions_video_link"), table_name="workflow_admissions")
    op.drop_index(op.f("ix_workflow_admissions_workflow_id"), table_name="workflow_admissions")
    op.drop_table("workflow_admissions")
