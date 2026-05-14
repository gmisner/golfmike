"""
Flight Events Storer - Handles flight status events and notifications
"""

from sqlalchemy.orm import Session
from models.sqlalchemy.flight_events import FlightEventsDBModel, TrackUpdatesDBModel
from utils.logger import main_logger as logger
from typing import Dict, Any
import json


def store_flight_events(flight_data: Dict[str, Any], session: Session) -> None:
    """
    Store flight events for status tracking and notifications

    Args:
        flight_data: Parsed flight data from XML
        session: Database session
    """
    try:
        aircraft_id = flight_data.get("aircraft_id")
        gufi = flight_data.get("gufi")

        if not aircraft_id or not gufi:
            logger.warning("Missing aircraft_id or gufi in flight data")
            return

        # Determine event type based on data
        event_type = determine_event_type(flight_data)

        # Create flight event record
        flight_event = FlightEventsDBModel(
            aircraft_id=aircraft_id,
            gufi=gufi,
            event_type=event_type,
            event_timestamp=flight_data.get("event_timestamp"),
            event_data=json.dumps(flight_data.get("event_data", {})),
            source_facility=flight_data.get("source_facility"),
        )

        session.add(flight_event)
        logger.info(f"Stored flight event: {aircraft_id} - {event_type}")

    except Exception as e:
        logger.error(f"Error storing flight events: {e}", exc_info=True)
        raise


def determine_event_type(flight_data: Dict[str, Any]) -> str:
    """
    Determine the flight event type based on the data

    Args:
        flight_data: Parsed flight data

    Returns:
        Event type string
    """
    # Check for specific status indicators
    status = flight_data.get("status", "").upper()

    if "DEPARTED" in status or "TAKEOFF" in status:
        return "DEPARTED"
    elif "ARRIVED" in status or "LANDED" in status:
        return "ARRIVED"
    elif "DIVERTED" in status:
        return "DIVERTED"
    elif "CANCELLED" in status:
        return "CANCELLED"
    elif "IN_FLIGHT" in status or "EN_ROUTE" in status:
        return "IN_FLIGHT"
    else:
        return "PLANNED"


def store_track_updates(track_data: Dict[str, Any], session: Session) -> None:
    """
    Store real-time track updates for position tracking

    Args:
        track_data: Parsed track data from XML
        session: Database session
    """
    try:
        aircraft_id = track_data.get("aircraft_id")
        gufi = track_data.get("gufi")

        if not aircraft_id or not gufi:
            logger.warning("Missing aircraft_id or gufi in track data")
            return

        # Extract position data
        position = track_data.get("position", {})
        latitude = position.get("latitude")
        longitude = position.get("longitude")

        if not latitude or not longitude:
            logger.warning(f"Missing position data for aircraft {aircraft_id}")
            return

        # Create track update record
        track_update = TrackUpdatesDBModel(
            aircraft_id=aircraft_id,
            gufi=gufi,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude=track_data.get("altitude"),
            speed=track_data.get("speed"),
            heading=track_data.get("heading"),
            time_at_position=track_data.get("time_at_position"),
            source_facility=track_data.get("source_facility"),
        )

        session.add(track_update)
        logger.info(f"Stored track update: {aircraft_id} at {latitude}, {longitude}")

    except Exception as e:
        logger.error(f"Error storing track updates: {e}", exc_info=True)
        raise



