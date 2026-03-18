"""initial schema — unified activity model

Revision ID: 0001_initial
Revises: None
Create Date: 2026-03-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # ── Enums ─────────────────────────────────────────────────────────
    venuetype = sa.Enum("outdoor_crag", "indoor_gym", name="venuetype")
    gradesystem = sa.Enum("french", "yds", "v_scale", "uiaa", "font", name="gradesystem")
    routestyle = sa.Enum("sport", "trad", "boulder", "multi_pitch", "alpine", name="routestyle")
    ticktype = sa.Enum(
        "onsight", "flash", "redpoint", "pinkpoint", "repeat", "attempt", "hang",
        name="ticktype",
    )
    activitysource = sa.Enum("intervals_icu", "manual", "csv_import", name="activitysource")

    # ── Crag ──────────────────────────────────────────────────────────
    op.create_table(
        "crag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name_normalized", sa.String(), nullable=True),
        sa.Column("country", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("region", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("venue_type", venuetype, nullable=False),
        sa.Column("default_grade_sys", gradesystem, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crag_name"), "crag", ["name"], unique=False)
    op.create_index(op.f("ix_crag_name_normalized"), "crag", ["name_normalized"], unique=False)

    # ── Area ──────────────────────────────────────────────────────────
    op.create_table(
        "area",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name_normalized", sa.String(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("crag_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crag_id"], ["crag.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_area_name_normalized"), "area", ["name_normalized"], unique=False)

    # ── Route ─────────────────────────────────────────────────────────
    op.create_table(
        "route",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name_normalized", sa.String(), nullable=True),
        sa.Column("grade", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("grade_system", gradesystem, nullable=False),
        sa.Column("style", routestyle, nullable=False),
        sa.Column("pitches", sa.Integer(), nullable=False),
        sa.Column("height_m", sa.Integer(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("crag_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"]),
        sa.ForeignKeyConstraint(["crag_id"], ["crag.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_route_name_normalized"), "route", ["name_normalized"], unique=False)

    # ── Activity (unified — replaces endurance_activity + climbing_session) ──
    op.create_table(
        "activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subtype", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source", activitysource, nullable=False),
        sa.Column("intervals_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("elevation_gain_m", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("training_load", sa.Float(), nullable=True),
        sa.Column("intensity", sa.Float(), nullable=True),
        sa.Column("crag_id", sa.Integer(), nullable=True),
        sa.Column("crag_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crag_id"], ["crag.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_date", "activity", ["date"], unique=False)
    op.create_index("ix_activity_type", "activity", ["type"], unique=False)
    op.create_index("ix_activity_intervals_id", "activity", ["intervals_id"], unique=True)
    op.create_index("ix_activity_crag_id", "activity", ["crag_id"], unique=False)
    op.create_index("uq_activity_date_crag", "activity", ["date", "crag_id"], unique=True)

    # ── Ascent ────────────────────────────────────────────────────────
    op.create_table(
        "ascent",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "tick_type",
            ticktype,
            nullable=False,
        ),
        sa.Column("tries", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("partner", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("crag_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("crag_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("route_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("grade", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activity.id"]),
        sa.ForeignKeyConstraint(["crag_id"], ["crag.id"]),
        sa.ForeignKeyConstraint(["route_id"], ["route.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ascent_crag_tick_date", "ascent", ["crag_id", "tick_type", "date"], unique=False)
    op.create_index("ix_ascent_activity_id", "ascent", ["activity_id"], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("ix_ascent_activity_id", table_name="ascent")
    op.drop_index("ix_ascent_crag_tick_date", table_name="ascent")
    op.drop_table("ascent")
    op.drop_index("uq_activity_date_crag", table_name="activity")
    op.drop_index("ix_activity_crag_id", table_name="activity")
    op.drop_index("ix_activity_intervals_id", table_name="activity")
    op.drop_index("ix_activity_type", table_name="activity")
    op.drop_index("ix_activity_date", table_name="activity")
    op.drop_table("activity")
    op.drop_index(op.f("ix_route_name_normalized"), table_name="route")
    op.drop_table("route")
    op.drop_index(op.f("ix_area_name_normalized"), table_name="area")
    op.drop_table("area")
    op.drop_index(op.f("ix_crag_name_normalized"), table_name="crag")
    op.drop_index(op.f("ix_crag_name"), table_name="crag")
    op.drop_table("crag")

    # Drop enums
    sa.Enum(name="activitysource").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ticktype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="routestyle").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="gradesystem").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="venuetype").drop(op.get_bind(), checkfirst=True)
