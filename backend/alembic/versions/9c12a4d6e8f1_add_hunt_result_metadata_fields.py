"""add hunt result metadata fields

Revision ID: 9c12a4d6e8f1
Revises: a7d4e6c1b912
Create Date: 2026-06-13 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c12a4d6e8f1"
down_revision: Union[str, None] = "a7d4e6c1b912"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hunts", sa.Column("title", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("summary", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("trust_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("hunts", "trust_score")
    op.drop_column("hunts", "summary")
    op.drop_column("hunts", "title")
