"""Add flight events, track updates, overlay, and flow prediction tables

Revision ID: 002
Revises: 001
Create Date: 2025-09-05 00:00:00

Creates all tables added during the Route Overlay, Notifications, and
Flow Probability features. Safe to run against a database that already has
the baseline tables from migration 001.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── flight_events ─────────────────────────────────────────────────────────
    op.create_table(
        "flight_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aircraft_id", sa.String(50), nullable=False),
        sa.Column("gufi", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_data", postgresql.JSONB()),
        sa.Column("source_facility", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_flight_events_aircraft_id", "flight_events", ["aircraft_id"])
    op.create_index("ix_flight_events_gufi", "flight_events", ["gufi"])
    op.create_index("ix_flight_events_event_type", "flight_events", ["event_type"])
    op.create_index("ix_flight_events_event_timestamp", "flight_events", ["event_timestamp"])

    # ── track_updates ─────────────────────────────────────────────────────────
    op.create_table(
        "track_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aircraft_id", sa.String(50), nullable=False),
        sa.Column("gufi", sa.String(50), nullable=False),
        sa.Column("latitude", sa.String(), nullable=False),
        sa.Column("longitude", sa.String(), nullable=False),
        sa.Column("altitude", sa.Integer()),
        sa.Column("speed", sa.Integer()),
        sa.Column("heading", sa.Integer()),
        sa.Column("time_at_position", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_facility", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_track_updates_aircraft_id", "track_updates", ["aircraft_id"])
    op.create_index("ix_track_updates_gufi", "track_updates", ["gufi"])
    op.create_index("ix_track_updates_time_at_position", "track_updates", ["time_at_position"])

    # ── aircraft_profiles ─────────────────────────────────────────────────────
    op.create_table(
        "aircraft_profiles",
        sa.Column("aircraft_id", sa.String(50), primary_key=True),
        sa.Column("airline", sa.String(10)),
        sa.Column("aircraft_type", sa.String(20)),
        sa.Column("aircraft_category", sa.String(20)),
        sa.Column("user_category", sa.String(30)),
        sa.Column("avatar_url", sa.String(255)),
        sa.Column("livery_colors", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── flight_routes ─────────────────────────────────────────────────────────
    op.create_table(
        "flight_routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aircraft_id", sa.String(50), nullable=False),
        sa.Column("gufi", sa.String(50), nullable=False),
        sa.Column("route_name", sa.String(100)),
        sa.Column("waypoints", postgresql.JSONB()),
        sa.Column("airways", postgresql.JSONB()),
        sa.Column("sectors", postgresql.JSONB()),
        sa.Column("route_of_flight", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_flight_routes_aircraft_id", "flight_routes", ["aircraft_id"])
    op.create_index("ix_flight_routes_gufi", "flight_routes", ["gufi"])

    # ── planned_waypoints ─────────────────────────────────────────────────────
    op.create_table(
        "planned_waypoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gufi", sa.String(100), nullable=False),
        sa.Column("aircraft_id", sa.String(50), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("fix_name", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("altitude_restriction", sa.String(20)),
        sa.Column("speed_restriction", sa.String(20)),
        sa.Column("estimated_time_over", sa.DateTime(timezone=True)),
        sa.Column("route_source", sa.String(20), server_default="FILED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_planned_waypoints_gufi", "planned_waypoints", ["gufi"])
    op.create_index("ix_planned_waypoints_aircraft_id", "planned_waypoints", ["aircraft_id"])
    op.create_index("ix_planned_waypoints_gufi_seq", "planned_waypoints", ["gufi", "sequence"])

    # ── flight_deviations ─────────────────────────────────────────────────────
    op.create_table(
        "flight_deviations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gufi", sa.String(100), nullable=False),
        sa.Column("aircraft_id", sa.String(50), nullable=False),
        sa.Column("actual_latitude", sa.Float(), nullable=False),
        sa.Column("actual_longitude", sa.Float(), nullable=False),
        sa.Column("actual_altitude", sa.Integer()),
        sa.Column("actual_speed", sa.Integer()),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nearest_planned_sequence", sa.Integer()),
        sa.Column("nearest_fix_name", sa.String(20)),
        sa.Column("cross_track_distance_nm", sa.Float()),
        sa.Column("altitude_delta_ft", sa.Integer()),
        sa.Column("alert_level", sa.String(20), server_default="NORMAL"),
        sa.Column("notification_sent", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_flight_deviations_gufi", "flight_deviations", ["gufi"])
    op.create_index("ix_flight_deviations_aircraft_id", "flight_deviations", ["aircraft_id"])
    op.create_index("ix_flight_deviations_gufi_ts", "flight_deviations", ["gufi", "timestamp"])

    # ── notification_subscriptions ────────────────────────────────────────────
    op.create_table(
        "notification_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("apprise_url", sa.String(500), nullable=False),
        sa.Column("label", sa.String(100)),
        sa.Column("event_types", postgresql.JSONB()),
        sa.Column("filter_origin", sa.String(10)),
        sa.Column("filter_destination", sa.String(10)),
        sa.Column("filter_aircraft_id", sa.String(50)),
        sa.Column("filter_alert_level", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_notified_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_notification_subscriptions_active",
        "notification_subscriptions",
        ["is_active"],
    )

    # ── flow_predictions ──────────────────────────────────────────────────────
    op.create_table(
        "flow_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("airport_icao", sa.String(10), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("window_hours", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("flow_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("ceiling_ft", sa.Integer()),
        sa.Column("visibility_sm", sa.Float()),
        sa.Column("flight_category", sa.String(10)),
        sa.Column("wind_speed_kt", sa.Integer()),
        sa.Column("wind_gust_kt", sa.Integer()),
        sa.Column("taf_trend", sa.String(20)),
        sa.Column("active_tmi_types", postgresql.JSONB()),
        sa.Column("active_sigmet", sa.Boolean(), server_default="false"),
        sa.Column("active_airmet_sierra", sa.Boolean(), server_default="false"),
        sa.Column("active_airmet_tango", sa.Boolean(), server_default="false"),
        sa.Column("arrival_count_1h", sa.Integer()),
        sa.Column("risk_factors", postgresql.JSONB()),
        sa.Column("feature_snapshot", postgresql.JSONB()),
        sa.Column("actual_flow_control", sa.Boolean()),
        sa.Column("actual_tmi_types", postgresql.JSONB()),
        sa.Column("labeled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_flow_predictions_airport_icao", "flow_predictions", ["airport_icao"])
    op.create_index("ix_flow_predictions_predicted_at", "flow_predictions", ["predicted_at"])
    op.create_index(
        "ix_flow_predictions_airport_ts",
        "flow_predictions",
        ["airport_icao", "predicted_at"],
    )


def downgrade() -> None:
    op.drop_table("flow_predictions")
    op.drop_table("notification_subscriptions")
    op.drop_table("flight_deviations")
    op.drop_table("planned_waypoints")
    op.drop_table("flight_routes")
    op.drop_table("aircraft_profiles")
    op.drop_table("track_updates")
    op.drop_table("flight_events")
