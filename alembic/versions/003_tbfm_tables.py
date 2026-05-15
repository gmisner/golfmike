"""003_tbfm_tables

TBFM (Traffic-Based Flow Management) tables:
  - tbfm_metering_flights  per-flight meter-fix schedule/sequence/delay
  - tbfm_tmis              Traffic Management Initiatives (GDP, AFP, GS …)
  - tbfm_raw_messages      raw XML samples for unknown/unparseable messages

Revision ID: 003
Revises: 002
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tbfm_metering_flights ─────────────────────────────────────────────────
    op.create_table(
        "tbfm_metering_flights",
        sa.Column("id",               sa.Integer,     primary_key=True),
        sa.Column("received_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("publication_type", sa.String(30),  nullable=True),
        sa.Column("airport",          sa.String(10),  nullable=True),
        sa.Column("aircraft_id",      sa.String(20),  nullable=True),
        sa.Column("gufi",             sa.String(100), nullable=True),
        sa.Column("meter_fix",        sa.String(20),  nullable=True),
        sa.Column("scheduled_time",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_time",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence_number",  sa.Integer,     nullable=True),
        sa.Column("delay_minutes",    sa.Integer,     nullable=True),
        sa.Column("arrival_runway",   sa.String(10),  nullable=True),
        sa.Column("flight_status",    sa.String(30),  nullable=True),
        sa.Column("extra_data",       JSONB,          nullable=True),
    )
    op.create_index("ix_tbfm_mf_gufi",        "tbfm_metering_flights", ["gufi"])
    op.create_index("ix_tbfm_mf_aircraft",    "tbfm_metering_flights", ["aircraft_id"])
    op.create_index("ix_tbfm_mf_airport",     "tbfm_metering_flights", ["airport"])
    op.create_index("ix_tbfm_mf_gufi_fix",    "tbfm_metering_flights", ["gufi", "meter_fix"])
    op.create_index("ix_tbfm_mf_airport_sched","tbfm_metering_flights", ["airport", "scheduled_time"])

    # ── tbfm_tmis ─────────────────────────────────────────────────────────────
    op.create_table(
        "tbfm_tmis",
        sa.Column("id",               sa.Integer,    primary_key=True),
        sa.Column("received_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("publication_type", sa.String(30), nullable=True),
        sa.Column("tmi_type",         sa.String(30), nullable=True),
        sa.Column("airport",          sa.String(10), nullable=True),
        sa.Column("program_name",     sa.String(80), nullable=True),
        sa.Column("start_time",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrival_rate",     sa.Integer,    nullable=True),
        sa.Column("extra_data",       JSONB,         nullable=True),
        sa.UniqueConstraint("tmi_type", "airport", "start_time",
                            name="uq_tbfm_tmi_type_airport_start"),
    )
    op.create_index("ix_tbfm_tmis_airport", "tbfm_tmis", ["airport"])

    # ── tbfm_raw_messages ─────────────────────────────────────────────────────
    op.create_table(
        "tbfm_raw_messages",
        sa.Column("id",           sa.Integer,    primary_key=True),
        sa.Column("received_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("root_element", sa.String(80), nullable=True),
        sa.Column("raw_xml",      sa.Text,       nullable=True),
        sa.Column("parse_error",  sa.Text,       nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tbfm_raw_messages")
    op.drop_index("ix_tbfm_tmis_airport",      table_name="tbfm_tmis")
    op.drop_table("tbfm_tmis")
    op.drop_index("ix_tbfm_mf_airport_sched",  table_name="tbfm_metering_flights")
    op.drop_index("ix_tbfm_mf_gufi_fix",       table_name="tbfm_metering_flights")
    op.drop_index("ix_tbfm_mf_airport",        table_name="tbfm_metering_flights")
    op.drop_index("ix_tbfm_mf_aircraft",       table_name="tbfm_metering_flights")
    op.drop_index("ix_tbfm_mf_gufi",           table_name="tbfm_metering_flights")
    op.drop_table("tbfm_metering_flights")
