"""add unique constraint on hunts video_link

Revision ID: f3a1c0b2d9e4
Revises: c31f9d4a2e11
Create Date: 2026-05-17 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f3a1c0b2d9e4"
down_revision: Union[str, None] = "c31f9d4a2e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_hunts_video_link",
        "hunts",
        ["video_link"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_hunts_video_link",
        "hunts",
        type_="unique",
    )
