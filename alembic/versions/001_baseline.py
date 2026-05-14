"""Baseline — represents schema created by Base.metadata.create_all()

Revision ID: 001
Revises:
Create Date: 2025-09-01 00:00:00

This migration is a no-op. The tables it covers were originally created by
db_config.init_db() which calls Base.metadata.create_all().

Upgrade paths
-------------
Fresh install (no existing database):
    The db_init service runs init_db() first, then `alembic upgrade head`.
    This migration will pass through harmlessly.

Existing deployment moving to Alembic:
    Run once to mark the baseline as applied without re-creating tables:
        alembic stamp 001
    Then apply new migrations:
        alembic upgrade head

Legacy tables covered by this baseline (created via create_all):
    upcoming_flights, flight_plan, aircraft, airspace_assignments,
    track_information, fltd_message, tmi_flight_list, tmi_updates,
    fxa_flight, status_updates, weather_stations, metar_data, taf_data,
    notam_data, weather_alerts, weather_observations, weather_stations_api,
    metar_data_api, taf_data_api, pirep_data_api, weather_alerts_api,
    weather_observations_api
"""

from typing import Sequence, Union

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
