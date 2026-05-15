"""add hunt status metadata and users table

Revision ID: b28a5e80b4f2
Revises: 66bbb0841ff5
Create Date: 2026-05-14 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b28a5e80b4f2"
down_revision: Union[str, None] = "66bbb0841ff5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hunts", sa.Column("status", sa.String(), nullable=False, server_default="queued"))
    op.add_column("hunts", sa.Column("thumbnail_url", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("caption", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("creator_handle", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("platform", sa.String(), nullable=False, server_default="instagram"))
    op.add_column("hunts", sa.Column("error_message", sa.String(), nullable=True))
    op.add_column("hunts", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hunts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hunts", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE hunts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE hunts SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    op.alter_column("hunts", "created_at", nullable=False)
    op.alter_column("hunts", "updated_at", nullable=False)

    op.create_table(
        "hunt_users",
        sa.Column("hunt_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["hunt_id"], ["hunts.id"]),
        sa.PrimaryKeyConstraint("hunt_id", "user_id"),
    )
    op.create_index(op.f("ix_hunt_users_hunt_id"), "hunt_users", ["hunt_id"], unique=False)
    op.create_index(op.f("ix_hunt_users_user_id"), "hunt_users", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hunt_users_user_id"), table_name="hunt_users")
    op.drop_index(op.f("ix_hunt_users_hunt_id"), table_name="hunt_users")
    op.drop_table("hunt_users")

    op.drop_column("hunts", "completed_at")
    op.drop_column("hunts", "updated_at")
    op.drop_column("hunts", "created_at")
    op.drop_column("hunts", "error_message")
    op.drop_column("hunts", "platform")
    op.drop_column("hunts", "creator_handle")
    op.drop_column("hunts", "caption")
    op.drop_column("hunts", "thumbnail_url")
    op.drop_column("hunts", "status")
