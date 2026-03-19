"""Add password_hash field to users table

Revision ID: 002_add_password_hash
Revises: 001_initial_schema
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_password_hash'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash column to users table
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=False, server_default=''))
    
    # Remove server_default after adding the column
    op.alter_column('users', 'password_hash', server_default=None)


def downgrade() -> None:
    # Remove password_hash column
    op.drop_column('users', 'password_hash')