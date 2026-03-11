"""Add region to activities; add tries/stars/url to session_routes

Revision ID: d4e5f6a7b8c9
Revises: cc006a6af522
Create Date: 2026-03-11 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # activities: add region for filtering by climbing area group
    op.add_column("activities", sa.Column("region", sa.Text(), nullable=True))
    op.create_index("ix_activities_region", "activities", ["region"])

    # session_routes: add enrichment fields from blog CSV / manual entry
    op.add_column("session_routes", sa.Column("tries", sa.Integer(), nullable=True))
    op.add_column("session_routes", sa.Column("stars", sa.Integer(), nullable=True))
    op.add_column("session_routes", sa.Column("url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_routes", "url")
    op.drop_column("session_routes", "stars")
    op.drop_column("session_routes", "tries")
    op.drop_index("ix_activities_region", table_name="activities")
    op.drop_column("activities", "region")
