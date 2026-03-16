"""add user_avatars.public_url

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-16

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_avatars", sa.Column("public_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_avatars", "public_url")
