"""add user hunt limits table

Revision ID: a7d4e6c1b912
Revises: f3a1c0b2d9e4
Create Date: 2026-05-17 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7d4e6c1b912"
down_revision: Union[str, None] = "f3a1c0b2d9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_hunt_limits",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("hunts_limit", sa.Integer(), nullable=False, server_default="30"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_hunt_limits_user_id"), "user_hunt_limits", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_hunt_limits_user_id"), table_name="user_hunt_limits")
    op.drop_table("user_hunt_limits")
