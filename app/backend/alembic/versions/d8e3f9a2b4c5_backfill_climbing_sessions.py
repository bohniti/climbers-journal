"""Backfill climbing sessions from existing ascents

Revision ID: d8e3f9a2b4c5
Revises: c7d2e8f1a3b4
Create Date: 2026-03-16 12:01:00.000000

"""
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "d8e3f9a2b4c5"
down_revision: Union[str, None] = "c7d2e8f1a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find distinct (date, crag_id) groups from ascents
    groups = conn.execute(
        sa.text("""
            SELECT DISTINCT a.date, a.crag_id, a.crag_name
            FROM ascent a
            WHERE a.crag_id IS NOT NULL AND a.session_id IS NULL
            ORDER BY a.date
        """)
    ).fetchall()

    logger.info("Backfilling %d climbing sessions from existing ascents", len(groups))
    created = 0

    for row_date, crag_id, crag_name in groups:
        # Insert session
        result = conn.execute(
            sa.text("""
                INSERT INTO climbing_session (date, crag_id, crag_name, created_at)
                VALUES (:date, :crag_id, :crag_name, NOW())
                ON CONFLICT (date, crag_id) DO UPDATE SET date = EXCLUDED.date
                RETURNING id
            """),
            {"date": row_date, "crag_id": crag_id, "crag_name": crag_name},
        )
        session_id = result.scalar()

        # Backfill session_id on matching ascents
        conn.execute(
            sa.text("""
                UPDATE ascent
                SET session_id = :session_id
                WHERE date = :date AND crag_id = :crag_id AND session_id IS NULL
            """),
            {"session_id": session_id, "date": row_date, "crag_id": crag_id},
        )
        created += 1

    # Check for orphaned ascents (NULL crag_id)
    orphan_count = conn.execute(
        sa.text("SELECT COUNT(*) FROM ascent WHERE crag_id IS NULL")
    ).scalar()
    if orphan_count:
        logger.warning(
            "Found %d ascents with NULL crag_id — these are not linked to any session",
            orphan_count,
        )

    logger.info("Created %d sessions, %d orphaned ascents skipped", created, orphan_count or 0)


def downgrade() -> None:
    conn = op.get_bind()
    # Clear session_id on all ascents
    conn.execute(sa.text("UPDATE ascent SET session_id = NULL"))
    # Delete all climbing sessions
    conn.execute(sa.text("DELETE FROM climbing_session"))
