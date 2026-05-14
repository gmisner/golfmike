#!/usr/bin/env python3
"""
CLI: compare track_information vs track_updates (and flight_plan / aircraft) for a tail number.

Usage:
  python tools/diagnose_aircraft_track.py N636CT
  python tools/diagnose_aircraft_track.py --tail n12345
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from db_config import engine
from utils.logger import main_logger as logger


def _run(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).fetchall()


def diagnose(tail_raw: str) -> int:
    tail = (tail_raw or "").strip().upper()
    if not tail:
        logger.error("Tail number is empty.")
        return 2

    print(f"=== Aircraft track diagnostic: {tail} ===\n")

    # Exact aircraft_id variants (common casing mistakes)
    for variant in (tail, tail.lower(), tail.capitalize()):
        try:
            rows = _run(
                "SELECT COUNT(*) AS n FROM track_information WHERE aircraft_id = :t",
                {"t": variant},
            )
            print(f"track_information rows (aircraft_id = {variant!r}): {rows[0][0]}")
        except Exception as e:
            logger.opt(exception=True).error("track_information count failed: {}", e)
            return 1

    try:
        rows = _run(
            """
            SELECT aircraft_id, COUNT(*) AS cnt,
                   SUM(CASE WHEN latitude IS NULL OR TRIM(COALESCE(latitude::text,'')) = '' THEN 1 ELSE 0 END) AS null_lat,
                   SUM(CASE WHEN longitude IS NULL OR TRIM(COALESCE(longitude::text,'')) = '' THEN 1 ELSE 0 END) AS null_lon
            FROM track_information
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            GROUP BY aircraft_id
            """,
            {"tail": tail},
        )
        if rows:
            for row in rows:
                print(
                    f"\ntrack_information (grouped) id={row[0]!r}: "
                    f"total={row[1]}, null_lat={row[2]}, null_lon={row[3]}"
                )
        else:
            print(
                f"\ntrack_information: no rows where UPPER(TRIM(aircraft_id)) = {tail!r}"
            )
    except Exception as e:
        logger.opt(exception=True).error("track_information aggregate failed: {}", e)
        return 1

    try:
        rows = _run(
            """
            SELECT aircraft_id, COUNT(*) AS cnt,
                   SUM(CASE WHEN latitude IS NULL OR TRIM(COALESCE(latitude::text,'')) = '' THEN 1 ELSE 0 END) AS null_lat,
                   SUM(CASE WHEN longitude IS NULL OR TRIM(COALESCE(longitude::text,'')) = '' THEN 1 ELSE 0 END) AS null_lon
            FROM track_updates
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            GROUP BY aircraft_id
            """,
            {"tail": tail},
        )
        if rows:
            for row in rows:
                print(
                    f"\ntrack_updates (grouped) id={row[0]!r}: "
                    f"total={row[1]}, null_lat={row[2]}, null_lon={row[3]}"
                )
        else:
            print(f"\ntrack_updates: no rows where UPPER(TRIM(aircraft_id)) = {tail!r}")
    except Exception as e:
        print(f"\ntrack_updates: query failed (table may be missing): {e}")

    try:
        rows = _run(
            """
            SELECT time_at_position, latitude, longitude, altitude, speed
            FROM track_information
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            ORDER BY time_at_position DESC NULLS LAST
            LIMIT 5
            """,
            {"tail": tail},
        )
        print("\n--- Last 5 track_information points ---")
        if rows:
            for row in rows:
                print(row)
        else:
            print("(none)")
    except Exception as e:
        logger.opt(exception=True).error("track_information sample failed: {}", e)
        return 1

    try:
        rows = _run(
            """
            SELECT time_at_position, latitude, longitude, altitude, speed
            FROM track_updates
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            ORDER BY time_at_position DESC NULLS LAST
            LIMIT 5
            """,
            {"tail": tail},
        )
        print("\n--- Last 5 track_updates points ---")
        if rows:
            for row in rows:
                print(row)
        else:
            print("(none)")
    except Exception as e:
        print(f"track_updates sample failed: {e}")

    try:
        rows = _run(
            """
            SELECT aircraft_id, gufi, departure_airport, arrival_airport, igtd,
                   "typeOfAircraft_03c" AS ac_type
            FROM flight_plan
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            ORDER BY igtd DESC NULLS LAST
            LIMIT 3
            """,
            {"tail": tail},
        )
        print("\n--- flight_plan (up to 3 latest) ---")
        if rows:
            for row in rows:
                print(row)
        else:
            print("(none)")
    except Exception as e:
        logger.opt(exception=True).error("flight_plan query failed: {}", e)
        return 1

    try:
        rows = _run(
            """
            SELECT aircraft_id, airline, aircraft_category, user_category
            FROM aircraft
            WHERE UPPER(TRIM(aircraft_id)) = :tail
            """,
            {"tail": tail},
        )
        print("\n--- aircraft ---")
        if rows:
            for row in rows:
                print(row)
        else:
            print("(none)")
    except Exception as e:
        logger.opt(exception=True).error("aircraft query failed: {}", e)
        return 1

    print("\nDone.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show track_information vs track_updates counts and samples for a tail number."
    )
    parser.add_argument(
        "tail",
        nargs="?",
        help="Aircraft registration (e.g. N636CT). Can also use --tail.",
    )
    parser.add_argument(
        "-t",
        "--tail",
        dest="tail_flag",
        metavar="REG",
        help="Same as positional tail (useful if the value starts with '-').",
    )
    args = parser.parse_args()
    raw = args.tail_flag or args.tail
    if not raw:
        parser.print_help()
        print(
            "\nError: provide a tail number, e.g.  python tools/diagnose_aircraft_track.py N636CT",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(diagnose(raw))


if __name__ == "__main__":
    main()
