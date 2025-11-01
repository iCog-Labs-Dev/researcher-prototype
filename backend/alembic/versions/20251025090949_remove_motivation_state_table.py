"""remove_motivation_state_table

Revision ID: 34efe3816279
Revises: 20250120000000
Create Date: 2025-10-25 09:09:49.254121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34efe3816279'
down_revision: Union[str, Sequence[str], None] = '20250120000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove motivation_states table."""
    # Drop index first
    op.drop_index('ix_motivation_states_active', table_name='motivation_states')
    
    # Drop the table
    op.drop_table('motivation_states')


def downgrade() -> None:
    """Downgrade schema - recreate motivation_states table."""
    # Recreate the table
    op.create_table('motivation_states',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('boredom', sa.Float(), nullable=False),
        sa.Column('curiosity', sa.Float(), nullable=False),
        sa.Column('tiredness', sa.Float(), nullable=False),
        sa.Column('satisfaction', sa.Float(), nullable=False),
        sa.Column('last_tick', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('meta_data', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate index
    op.create_index('ix_motivation_states_active', 'motivation_states', ['is_active'], unique=False)
