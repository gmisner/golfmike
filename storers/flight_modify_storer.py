"""
Storer for flight modification and amendment delta messages.

Both parse_flight_modify and parse_flight_plan_amendment return the same
normalised dict shape, so this single storer handles both.  It does a
targeted UPDATE against the existing FlightPlanDBModel row keyed by GUFI.

Side-effects when route changes:
  - Re-decodes the route via route_decoder
  - Stores updated planned_waypoints with route_source="AMENDED"
  - Fires a FILED notification with the amended route
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db_config import SessionLocal
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from services.notification_service import send_flight_event
from services.route_decoder import decode_route
from services.route_overlay_service import store_planned_waypoints
from utils.logger import main_logger as logger


# Maps the normalised dict keys to FlightPlanDBModel column names
_FIELD_MAP: dict[str, str] = {
    "aircraft_id": "aircraft_id",
    "departure_airport": "departure_airport",
    "arrival_airport": "arrival_airport",
    "departure_time": "igtd",
    "route_text": "flightPlanRoute_10a",
    "aircraft_type": "typeOfAircraft_03c",
    "source_facility": "source_facility",
}


def store_flight_modification(
    modify_data: Optional[dict[str, Any]],
    session: Optional[Session] = None,
) -> bool:
    """
    Apply a flight modification delta to the existing FlightPlanDBModel row.

    Returns True on success, False if the record was not found or an error
    occurred (does not raise — callers should check the return value).
    """
    if not modify_data:
        return False

    gufi = modify_data.get("gufi")
    if not gufi:
        logger.warning("store_flight_modification called with no GUFI")
        return False

    created_locally = session is None
    if session is None:
        session = SessionLocal()

    try:
        fp = session.query(FlightPlanDBModel).filter_by(gufi=gufi).first()

        if fp is None:
            logger.warning(
                f"No FlightPlanDBModel found for GUFI {gufi!r} — "
                "modification cannot be applied (flight not yet in DB)"
            )
            return False

        updated_fields: list[str] = []
        for src_key, col_name in _FIELD_MAP.items():
            value = modify_data.get(src_key)
            if value is not None and hasattr(fp, col_name):
                setattr(fp, col_name, value)
                updated_fields.append(col_name)

        if not updated_fields:
            logger.info(f"flightModification for {gufi!r} contained no updatable fields")
            return True

        session.commit()
        logger.info(
            f"Updated FlightPlanDBModel {gufi!r} "
            f"[{modify_data.get('amendment_type', 'MODIFY')}]: {updated_fields}"
        )

        # ── If route changed, re-decode and update planned waypoints ──────────
        new_route = modify_data.get("route_text")
        if new_route:
            departure = modify_data.get("departure_airport") or getattr(fp, "departure_airport", "")
            destination = modify_data.get("arrival_airport") or getattr(fp, "arrival_airport", "")
            aircraft_id = modify_data.get("aircraft_id") or getattr(fp, "aircraft_id", "")

            try:
                waypoints = decode_route(new_route, departure, destination)
                n = store_planned_waypoints(
                    gufi=gufi,
                    aircraft_id=aircraft_id,
                    waypoints=waypoints,
                    session=session,
                    route_source="AMENDED",
                )
                logger.info(f"Stored {n} amended waypoints for {aircraft_id} ({gufi})")
            except Exception as e:
                logger.error(f"Route decode failed for amended flight {gufi!r}: {e}", exc_info=True)

            # Notify subscribers of the route change
            try:
                send_flight_event(
                    "FILED",
                    {
                        "aircraft_id": aircraft_id,
                        "gufi": gufi,
                        "departure_airport": departure,
                        "arrival_airport": destination,
                        "route_text": new_route,
                        "amendment_type": modify_data.get("amendment_type", "MODIFY"),
                    },
                    session,
                )
            except Exception as e:
                logger.error(f"Notification failed for amended flight {gufi!r}: {e}", exc_info=True)

        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"DB error applying flightModification for {gufi!r}: {e}", exc_info=True)
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in store_flight_modification for {gufi!r}: {e}", exc_info=True)
        return False
    finally:
        if created_locally:
            session.close()
