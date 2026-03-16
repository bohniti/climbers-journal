"""add ix_ascent_date index

Revision ID: b3f1a2c4d5e6
Revises: a25ec3f6c41d
Create Date: 2026-03-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3f1a2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a25ec3f6c41d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add date index on ascent table for weekly queries."""
    op.create_index('ix_ascent_date', 'ascent', ['date'], unique=False)


def downgrade() -> None:
    """Remove date index."""
    op.drop_index('ix_ascent_date', table_name='ascent')
