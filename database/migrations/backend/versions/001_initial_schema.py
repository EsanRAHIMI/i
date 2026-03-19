"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-10-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(length=50), server_default='UTC', nullable=True),
        sa.Column('language_preference', sa.String(length=10), server_default='fa-IR', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create user_settings table
    op.create_table('user_settings',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('whatsapp_opt_in', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('voice_training_consent', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('calendar_sync_enabled', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('privacy_level', sa.String(length=20), server_default='standard', nullable=True),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create calendars table
    op.create_table('calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('google_calendar_id', sa.String(length=255), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('sync_token', sa.String(length=255), nullable=True),
        sa.Column('last_sync_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('webhook_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create events table
    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('google_event_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.TIMESTAMP(), nullable=False),
        sa.Column('end_time', sa.TIMESTAMP(), nullable=False),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('attendees', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('ai_generated', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['calendar_id'], ['calendars.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), server_default='3', nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=True),
        sa.Column('due_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('created_by_ai', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create whatsapp_threads table
    op.create_table('whatsapp_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('thread_status', sa.String(length=20), server_default='active', nullable=True),
        sa.Column('last_message_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create whatsapp_messages table
    op.create_table('whatsapp_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=True),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=20), server_default='text', nullable=True),
        sa.Column('status', sa.String(length=20), server_default='sent', nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['whatsapp_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )

    # Create federated_rounds table
    op.create_table('federated_rounds',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('aggregation_status', sa.String(length=20), server_default='in_progress', nullable=True),
        sa.Column('participant_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create client_updates table
    op.create_table('client_updates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('round_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_delta_encrypted', sa.Text(), nullable=False),
        sa.Column('privacy_budget_used', sa.DECIMAL(precision=10, scale=8), nullable=True),
        sa.Column('uploaded_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['round_id'], ['federated_rounds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create consents table
    op.create_table('consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('consent_text', sa.Text(), nullable=False),
        sa.Column('granted_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('revoked_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_events_user_id_start_time', 'events', ['user_id', 'start_time'])
    op.create_index('idx_tasks_user_id_status', 'tasks', ['user_id', 'status'])
    op.create_index('idx_whatsapp_messages_thread_id_sent_at', 'whatsapp_messages', ['thread_id', 'sent_at'])
    op.create_index('idx_audit_logs_user_id_created_at', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('idx_federated_rounds_round_number', 'federated_rounds', ['round_number'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_federated_rounds_round_number')
    op.drop_index('idx_audit_logs_user_id_created_at')
    op.drop_index('idx_whatsapp_messages_thread_id_sent_at')
    op.drop_index('idx_tasks_user_id_status')
    op.drop_index('idx_events_user_id_start_time')
    op.drop_index('idx_users_email')
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('audit_logs')
    op.drop_table('consents')
    op.drop_table('client_updates')
    op.drop_table('federated_rounds')
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_threads')
    op.drop_table('tasks')
    op.drop_table('events')
    op.drop_table('calendars')
    op.drop_table('user_settings')
    op.drop_table('users')