#!/usr/bin/env python3
"""Add SFDPS operational columns to flights table."""

from sqlalchemy import text

from db_config import engine
from utils.logger import main_logger as logger


def main() -> None:
    logger.info("Updating flights schema with SFDPS operational columns")
    statements = [
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS source_timestamp TIMESTAMPTZ",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS route_text TEXT",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS current_beacon_code VARCHAR(10)",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS fdps_flight_status VARCHAR(50)",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS coordination_time TIMESTAMPTZ",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS coordination_fix VARCHAR(20)",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS coordination_distance_nm DOUBLE PRECISION",
        "ALTER TABLE flights ADD COLUMN IF NOT EXISTS coordination_radial_deg DOUBLE PRECISION",
        "CREATE INDEX IF NOT EXISTS idx_flights_fdps_flight_status ON flights(fdps_flight_status)",
        "CREATE INDEX IF NOT EXISTS idx_flights_coordination_time ON flights(coordination_time)",
    ]
    with engine.connect() as conn:
        for sql in statements:
            conn.execute(text(sql))
        conn.commit()
    logger.success("Flights schema update complete")


if __name__ == "__main__":
    main()
