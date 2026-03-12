"""Add avg_heart_rate and calories to activities

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("avg_heart_rate", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("calories", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("activities", "calories")
    op.drop_column("activities", "avg_heart_rate")
