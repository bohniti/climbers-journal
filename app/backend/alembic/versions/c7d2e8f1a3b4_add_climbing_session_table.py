"""Add climbing_session table and session_id to ascent

Revision ID: c7d2e8f1a3b4
Revises: b3f1a2c4d5e6
Create Date: 2026-03-16 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2e8f1a3b4"
down_revision: Union[str, None] = "b3f1a2c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create climbing_session table
    op.create_table(
        "climbing_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("crag_id", sa.Integer(), nullable=False),
        sa.Column("crag_name", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("linked_activity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crag_id"], ["crag.id"]),
        sa.ForeignKeyConstraint(["linked_activity_id"], ["endurance_activity.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_date", "climbing_session", ["date"])
    op.create_index("ix_session_crag_id", "climbing_session", ["crag_id"])
    op.create_index(
        "uq_session_date_crag", "climbing_session", ["date", "crag_id"], unique=True
    )

    # Add session_id FK to ascent
    op.add_column("ascent", sa.Column("session_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ascent_session_id", "ascent", "climbing_session", ["session_id"], ["id"]
    )
    op.create_index("ix_ascent_session_id", "ascent", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_ascent_session_id", table_name="ascent")
    op.drop_constraint("fk_ascent_session_id", "ascent", type_="foreignkey")
    op.drop_column("ascent", "session_id")
    op.drop_index("uq_session_date_crag", table_name="climbing_session")
    op.drop_index("ix_session_crag_id", table_name="climbing_session")
    op.drop_index("ix_session_date", table_name="climbing_session")
    op.drop_table("climbing_session")
