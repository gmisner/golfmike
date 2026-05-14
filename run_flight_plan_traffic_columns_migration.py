#!/usr/bin/env python3
"""
Apply migrations/005_flight_plan_traffic_columns.sql.

Adds "flightPlanRoute_10a" and "flightId_02a" on public.flight_plan if missing.
Uses db_config engine (same as the app).
"""

from pathlib import Path

from sqlalchemy import text

from db_config import engine
from utils.logger import main_logger as logger


def main() -> None:
    sql_path = (
        Path(__file__).resolve().parent
        / "migrations"
        / "005_flight_plan_traffic_columns.sql"
    )
    if not sql_path.is_file():
        logger.error("Migration file not found: {}", sql_path)
        raise SystemExit(1)

    sql = sql_path.read_text(encoding="utf-8")
    logger.info("Applying flight_plan traffic columns migration from {}", sql_path)

    # Single DO $$ ... $$ block — must not split on inner semicolons
    with engine.begin() as conn:
        conn.execute(text(sql))

    logger.success("Flight plan traffic columns migration completed.")


if __name__ == "__main__":
    main()
