"""drop legacy motivation drive columns

Revision ID: 20260106100000
Revises: 64dcb4c7f0d9
Create Date: 2026-01-06 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260106100000"
down_revision: Union[str, Sequence[str], None] = "64dcb4c7f0d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unused legacy motivation drive columns."""
    with op.batch_alter_table("motivation_configs") as batch_op:
        for col in ("boredom_rate", "curiosity_decay", "tiredness_decay", "satisfaction_decay"):
            batch_op.drop_column(col)


def downgrade() -> None:
    """Recreate legacy motivation drive columns."""
    with op.batch_alter_table("motivation_configs") as batch_op:
        batch_op.add_column(sa.Column("boredom_rate", sa.Float(), nullable=False, server_default="0.0002"))
        batch_op.add_column(sa.Column("curiosity_decay", sa.Float(), nullable=False, server_default="0.0002"))
        batch_op.add_column(sa.Column("tiredness_decay", sa.Float(), nullable=False, server_default="0.0002"))
        batch_op.add_column(sa.Column("satisfaction_decay", sa.Float(), nullable=False, server_default="0.0002"))

