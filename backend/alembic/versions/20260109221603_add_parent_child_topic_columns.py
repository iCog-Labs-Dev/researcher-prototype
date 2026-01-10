"""add parent child topic columns

Revision ID: 20260109221603
Revises: 20260106100000
Create Date: 2026-01-09 22:16:03.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260109221603"
down_revision: Union[str, Sequence[str], None] = "20260106100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_child and parent_id columns to research_topics table."""
    with op.batch_alter_table("research_topics") as batch_op:
        # Add is_child boolean column with default False
        batch_op.add_column(sa.Column("is_child", sa.Boolean(), nullable=False, server_default="false"))
        
        # Add parent_id UUID column (nullable, will be FK)
        batch_op.add_column(sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True))
        
        # Create foreign key constraint
        batch_op.create_foreign_key(
            "fk_research_topics_parent_id",
            "research_topics",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE"
        )
        
        # Create index on parent_id for efficient child queries
        batch_op.create_index("ix_research_topics_parent_id", ["parent_id"])


def downgrade() -> None:
    """Remove is_child and parent_id columns from research_topics table."""
    with op.batch_alter_table("research_topics") as batch_op:
        # Drop index first
        batch_op.drop_index("ix_research_topics_parent_id")
        
        # Drop foreign key constraint
        batch_op.drop_constraint("fk_research_topics_parent_id", type_="foreignkey")
        
        # Drop columns
        batch_op.drop_column("parent_id")
        batch_op.drop_column("is_child")
