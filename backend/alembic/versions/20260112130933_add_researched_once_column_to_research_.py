"""add researched_once column to research_topics

Revision ID: 3bbec4741886
Revises: 20260109221603
Create Date: 2026-01-12 13:09:33.472163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bbec4741886'
down_revision: Union[str, Sequence[str], None] = '20260109221603'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add researched_once column to research_topics table."""
    with op.batch_alter_table("research_topics") as batch_op:
        batch_op.add_column(sa.Column("researched_once", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    """Remove researched_once column from research_topics table."""
    with op.batch_alter_table("research_topics") as batch_op:
        batch_op.drop_column("researched_once")
