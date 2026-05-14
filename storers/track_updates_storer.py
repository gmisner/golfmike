"""
Track Updates Storer - Stores position updates to track_updates table
Links via aircraft_id → GUFI relationship
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db_config import SessionLocal
from utils.aircraft_id import normalize_aircraft_id
from utils.db_metrics import log_db_write_duration
from utils.geo_validation import validate_wgs84_lat_lon
from utils.logger import main_logger as logger


def _json_safe(value: Any) -> Any:
    """Recursively convert values so json.dumps never sees lxml _Attrib or other non-JSON types."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    # dict and lxml _Attrib are both Mapping; _Attrib is not a dict subclass
    if isinstance(value, Mapping):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def store_track_update(
    track_data: Dict[str, Any],
    session: Session = None,
) -> None:
    """
    Store a single track update to track_updates table

    Args:
        track_data: Dictionary containing parsed track information
        session: SQLAlchemy session (optional, will create if not provided)
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    elif not isinstance(session, Session):
        logger.error(
            "Invalid session type: {}. Expected <class 'sqlalchemy.orm.session.Session'>.",
            type(session),
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    try:
        aircraft_id = normalize_aircraft_id(track_data.get("aircraft_id"))
        gufi = track_data.get("gufi")
        latitude = track_data.get("latitude")
        longitude = track_data.get("longitude")

        if not aircraft_id:
            logger.warning("No aircraft_id found in track data, skipping")
            return

        if not latitude or not longitude:
            logger.warning(
                f"Missing position data for aircraft {aircraft_id}, skipping"
            )
            return

        # If no GUFI, try to find one from flight_plan or flights table using aircraft_id
        # This is the proper relationship: aircraft_id → flight_plan/flights → GUFI
        if not gufi:
            # First try flights table (most recent flight for this aircraft)
            result = session.execute(
                text(
                    """
                    SELECT gufi FROM flights 
                    WHERE aircraft_id = :aircraft_id 
                    ORDER BY updated_at DESC
                    LIMIT 1
                """
                ),
                {"aircraft_id": aircraft_id},
            )
            row = result.fetchone()
            if row and row[0]:
                gufi = row[0]
                logger.debug(
                    f"Found GUFI {gufi} from flights table for aircraft {aircraft_id}"
                )
            else:
                # Fallback: try flight_plan table
                result = session.execute(
                    text(
                        """
                        SELECT gufi FROM flight_plan 
                        WHERE aircraft_id = :aircraft_id 
                        AND gufi IS NOT NULL
                        ORDER BY id DESC
                        LIMIT 1
                    """
                    ),
                    {"aircraft_id": aircraft_id},
                )
                row = result.fetchone()
                if row and row[0]:
                    gufi = row[0]
                    logger.debug(
                        f"Found GUFI {gufi} from flight_plan table for aircraft {aircraft_id}"
                    )

        # If still no GUFI, create a temporary one to ensure track updates are stored
        # This handles cases where track updates arrive before flight plans
        if not gufi:
            import hashlib

            timestamp_str = datetime.utcnow().isoformat()
            gufi_input = f"{aircraft_id}_{timestamp_str}"
            gufi = f"TEMP_TRACK_{hashlib.md5(gufi_input.encode()).hexdigest()[:12].upper()}"
            logger.debug(
                f"Created temporary GUFI {gufi} for track update of aircraft {aircraft_id}"
            )

        try:
            lat_float = float(latitude) if latitude else None
            lon_float = float(longitude) if longitude else None
        except (ValueError, TypeError):
            logger.warning(
                "Invalid coordinates for aircraft {}: lat={}, lon={}",
                aircraft_id,
                latitude,
                longitude,
            )
            return

        ok_bounds, bound_msg = validate_wgs84_lat_lon(lat_float, lon_float)
        if not ok_bounds:
            logger.warning(
                "Coordinates out of range for aircraft {}: {}",
                aircraft_id,
                bound_msg,
            )
            return

        with log_db_write_duration(
            "track_update_write",
            aircraft_id=aircraft_id,
            gufi=gufi,
        ):
            # Ensure aircraft exists
            session.execute(
                text(
                    """
                    INSERT INTO aircraft (aircraft_id)
                    VALUES (:aircraft_id)
                    ON CONFLICT (aircraft_id) DO NOTHING
                """
                ),
                {"aircraft_id": aircraft_id},
            )

            # Ensure flight exists in flights table (required for foreign key)
            session.execute(
                text(
                    """
                    INSERT INTO flights (gufi, aircraft_id, updated_at)
                    VALUES (:gufi, :aircraft_id, NOW())
                    ON CONFLICT (gufi)
                    DO UPDATE SET
                        aircraft_id = EXCLUDED.aircraft_id,
                        updated_at = NOW()
                """
                ),
                {
                    "gufi": gufi,
                    "aircraft_id": aircraft_id,
                },
            )

            def parse_datetime(dt_str):
                if not dt_str:
                    return datetime.utcnow()
                try:
                    if isinstance(dt_str, datetime):
                        return dt_str
                    return datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
                except Exception:
                    try:
                        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"]:
                            return datetime.strptime(str(dt_str), fmt)
                    except Exception:
                        logger.warning(
                            "Could not parse datetime: {}, using current time", dt_str
                        )
                        return datetime.utcnow()

            time_at_position = parse_datetime(track_data.get("time_at_position"))

            import json

            track_data_json = None
            raw_td = track_data.get("track_data")
            if raw_td is not None:
                track_data_json = json.dumps(_json_safe(raw_td))

            session.execute(
                text(
                    """
                    INSERT INTO track_updates
                    (aircraft_id, gufi, latitude, longitude, altitude, speed, heading,
                     time_at_position, source_facility, track_data)
                    VALUES (:aircraft_id, :gufi, :lat, :lon, :alt, :speed, :heading,
                            :time_at_pos, :facility, CAST(:track_data_json AS jsonb))
                """
                ),
                {
                    "aircraft_id": aircraft_id,
                    "gufi": gufi,
                    "lat": lat_float,
                    "lon": lon_float,
                    "alt": track_data.get("altitude"),
                    "speed": track_data.get("speed"),
                    "heading": track_data.get("heading"),
                    "time_at_pos": time_at_position,
                    "facility": track_data.get("source_facility"),
                    "track_data_json": track_data_json,
                },
            )

            session.execute(
                text(
                    """
                    UPDATE flights
                    SET current_status = 'IN_FLIGHT',
                        updated_at = NOW()
                    WHERE gufi = :gufi
                    AND current_status = 'PLANNED'
                """
                ),
                {"gufi": gufi},
            )

            session.commit()
        logger.debug(f"Stored track update for aircraft {aircraft_id}, GUFI {gufi}")

    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError storing track update: {}", str(e), exc_info=True)
        session.rollback()
        raise
    except Exception as e:
        logger.error("Error storing track update: {}", str(e), exc_info=True)
        session.rollback()
        raise
    finally:
        if created_locally:
            session.close()


def store_track_updates(
    track_data_list: List[Dict[str, Any]],
    session: Session = None,
) -> None:
    """
    Store multiple track updates

    Args:
        track_data_list: List of dictionaries containing parsed track information
        session: SQLAlchemy session (optional, will create if not provided)
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True

    try:
        for track_data in track_data_list:
            store_track_update(track_data, session=session)

        logger.success(f"Successfully stored {len(track_data_list)} track updates")
    except Exception as e:
        logger.error("Error storing track updates: {}", str(e), exc_info=True)
        raise
    finally:
        if created_locally:
            session.close()
