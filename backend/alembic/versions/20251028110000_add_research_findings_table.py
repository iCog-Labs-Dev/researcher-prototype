"""add research_findings table

Revision ID: 20251028110000
Revises: 34efe3816279
Create Date: 2025-10-28 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251028110000'
down_revision = '34efe3816279'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'research_findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic_name', sa.String(length=255), nullable=False),
        sa.Column('finding_id', sa.String(length=255), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('bookmarked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('integrated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('research_time', sa.Float(), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.UniqueConstraint('user_id', 'finding_id', name='uq_research_finding_user_finding'),
    )
    op.create_index('ix_findings_user_topic', 'research_findings', ['user_id', 'topic_name'])
    op.create_index('ix_findings_time', 'research_findings', ['research_time'])


def downgrade() -> None:
    op.drop_index('ix_findings_time', table_name='research_findings')
    op.drop_index('ix_findings_user_topic', table_name='research_findings')
    op.drop_table('research_findings')


