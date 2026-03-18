"""add user_avatars table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-16

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
except Exception:  # pragma: no cover
    PGUUID = None


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = sa.String(length=36)
    op.create_table(
        "user_avatars",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_avatars_user_id", "user_avatars", ["user_id"], unique=False)
    op.create_index("ix_user_avatars_filename", "user_avatars", ["filename"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_avatars_filename", table_name="user_avatars")
    op.drop_index("ix_user_avatars_user_id", table_name="user_avatars")
    op.drop_table("user_avatars")
