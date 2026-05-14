"""
API Endpoints for Real-Time Flight Tracking
"""

from flask import Flask, jsonify, request
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from db_config import SessionLocal
from models.sqlalchemy.flight_events import (
    FlightEventsDBModel,
    TrackUpdatesDBModel,
    AircraftProfilesDBModel,
)
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_plan import FlightPlanDBModel
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger
from typing import Dict, List, Any
import json


def create_flight_tracking_api(app: Flask) -> None:
    def _normalize_lookup_aircraft_id(raw: str | None) -> str:
        return normalize_aircraft_id(raw) or ""

    """Add flight tracking endpoints to the Flask app"""

    @app.route("/api/flights/current", methods=["GET"])
    def get_current_flights():
        """Get all currently active flights with their latest positions"""
        try:
            session = SessionLocal()

            # Simple query to get flight plans
            flights_query = session.query(FlightPlanDBModel).limit(50).all()
            flights = []

            for flight in flights_query:
                flight_data = {
                    "aircraft_id": flight.aircraft_id,
                    "gufi": flight.gufi,
                    "departure_airport": flight.departure_airport,
                    "arrival_airport": flight.arrival_airport,
                    "scheduled_departure": (
                        flight.igtd.isoformat() if flight.igtd else None
                    ),
                    "scheduled_arrival": (
                        flight.eta.isoformat() if flight.eta else None
                    ),
                    "current_status": "PLANNED",  # Default status
                    "status_timestamp": None,
                    "position": {
                        "latitude": None,
                        "longitude": None,
                        "altitude": None,
                        "speed": None,
                        "heading": None,
                        "timestamp": None,
                    },
                }
                flights.append(flight_data)

            session.close()
            return jsonify({"flights": flights, "count": len(flights)})

        except Exception as e:
            logger.error(f"Error getting current flights: {e}", exc_info=True)
            return jsonify({"error": "Failed to get current flights"}), 500

    @app.route("/api/flights/<aircraft_id>/position", methods=["GET"])
    def get_aircraft_position(aircraft_id: str):
        """Get current position of a specific aircraft"""
        try:
            session = SessionLocal()

            aid = _normalize_lookup_aircraft_id(aircraft_id)
            if not aid:
                session.close()
                return jsonify({"error": "Aircraft not found"}), 404

            # Get latest position
            latest_track = (
                session.query(TrackUpdatesDBModel)
                .filter(TrackUpdatesDBModel.aircraft_id == aid)
                .order_by(TrackUpdatesDBModel.time_at_position.desc())
                .first()
            )

            if not latest_track:
                session.close()
                return jsonify({"error": "Aircraft not found"}), 404

            position = {
                "aircraft_id": latest_track.aircraft_id,
                "gufi": latest_track.gufi,
                "latitude": float(latest_track.latitude),
                "longitude": float(latest_track.longitude),
                "altitude": latest_track.altitude,
                "speed": latest_track.speed,
                "heading": latest_track.heading,
                "timestamp": latest_track.time_at_position.isoformat(),
                "source_facility": latest_track.source_facility,
            }

            session.close()
            return jsonify(position)

        except Exception as e:
            logger.error(f"Error getting aircraft position: {e}", exc_info=True)
            return jsonify({"error": "Failed to get aircraft position"}), 500

    @app.route("/api/flights/<aircraft_id>/track", methods=["GET"])
    def get_aircraft_track(aircraft_id: str):
        """Get track history for a specific aircraft"""
        try:
            session = SessionLocal()

            aid = _normalize_lookup_aircraft_id(aircraft_id)
            if not aid:
                session.close()
                return jsonify({"aircraft_id": "", "tracks": []})

            # Get track history (last 24 hours by default)
            hours_back = request.args.get("hours", 24, type=int)

            tracks = (
                session.query(TrackUpdatesDBModel)
                .filter(
                    TrackUpdatesDBModel.aircraft_id == aid,
                    TrackUpdatesDBModel.time_at_position
                    >= func.now() - func.interval(f"{hours_back} hours"),
                )
                .order_by(TrackUpdatesDBModel.time_at_position.desc())
                .all()
            )

            track_data = []
            for track in tracks:
                track_data.append(
                    {
                        "latitude": float(track.latitude),
                        "longitude": float(track.longitude),
                        "altitude": track.altitude,
                        "speed": track.speed,
                        "heading": track.heading,
                        "timestamp": track.time_at_position.isoformat(),
                    }
                )

            session.close()
            return jsonify({"aircraft_id": aid, "tracks": track_data})

        except Exception as e:
            logger.error(f"Error getting aircraft track: {e}", exc_info=True)
            return jsonify({"error": "Failed to get aircraft track"}), 500

    @app.route("/api/flights/<aircraft_id>/status", methods=["GET"])
    def get_aircraft_status(aircraft_id: str):
        """Get flight status and events for a specific aircraft"""
        try:
            session = SessionLocal()

            aid = _normalize_lookup_aircraft_id(aircraft_id)
            if not aid:
                session.close()
                return jsonify({"error": "Aircraft not found"}), 404

            # Get flight plan
            flight_plan = (
                session.query(FlightPlanDBModel)
                .filter(FlightPlanDBModel.aircraft_id == aid)
                .first()
            )

            # Get recent events
            events = (
                session.query(FlightEventsDBModel)
                .filter(FlightEventsDBModel.aircraft_id == aid)
                .order_by(FlightEventsDBModel.event_timestamp.desc())
                .limit(10)
                .all()
            )

            # Get aircraft profile
            profile = (
                session.query(AircraftProfilesDBModel)
                .filter(AircraftProfilesDBModel.aircraft_id == aid)
                .first()
            )

            status_data = {
                "aircraft_id": aid,
                "flight_plan": (
                    {
                        "gufi": flight_plan.gufi if flight_plan else None,
                        "departure_airport": (
                            flight_plan.departure_airport if flight_plan else None
                        ),
                        "arrival_airport": (
                            flight_plan.arrival_airport if flight_plan else None
                        ),
                        "scheduled_departure": (
                            flight_plan.igtd.isoformat()
                            if flight_plan and flight_plan.igtd
                            else None
                        ),
                        "scheduled_arrival": (
                            flight_plan.eta.isoformat()
                            if flight_plan and flight_plan.eta
                            else None
                        ),
                    }
                    if flight_plan
                    else None
                ),
                "aircraft_profile": (
                    {
                        "airline": profile.airline if profile else None,
                        "aircraft_type": profile.aircraft_type if profile else None,
                        "aircraft_category": (
                            profile.aircraft_category if profile else None
                        ),
                        "user_category": profile.user_category if profile else None,
                        "avatar_url": profile.avatar_url if profile else None,
                    }
                    if profile
                    else None
                ),
                "recent_events": [
                    {
                        "event_type": event.event_type,
                        "timestamp": event.event_timestamp.isoformat(),
                        "data": event.event_data,
                    }
                    for event in events
                ],
            }

            session.close()
            return jsonify(status_data)

        except Exception as e:
            logger.error(f"Error getting aircraft status: {e}", exc_info=True)
            return jsonify({"error": "Failed to get aircraft status"}), 500

    @app.route("/api/flights/notifications", methods=["GET"])
    def get_flight_notifications():
        """Get recent flight notifications (takeoffs, landings, etc.)"""
        try:
            session = SessionLocal()

            # Get recent events
            hours_back = request.args.get("hours", 1, type=int)

            events = (
                session.query(FlightEventsDBModel)
                .filter(
                    FlightEventsDBModel.event_timestamp
                    >= func.now() - func.interval(f"{hours_back} hours"),
                    FlightEventsDBModel.event_type.in_(
                        ["DEPARTED", "ARRIVED", "DIVERTED", "CANCELLED"]
                    ),
                )
                .order_by(FlightEventsDBModel.event_timestamp.desc())
                .limit(50)
                .all()
            )

            notifications = []
            for event in events:
                notification = {
                    "aircraft_id": event.aircraft_id,
                    "gufi": event.gufi,
                    "event_type": event.event_type,
                    "timestamp": event.event_timestamp.isoformat(),
                    "data": event.event_data,
                }
                notifications.append(notification)

            session.close()
            return jsonify(
                {"notifications": notifications, "count": len(notifications)}
            )

        except Exception as e:
            logger.error(f"Error getting flight notifications: {e}", exc_info=True)
            return jsonify({"error": "Failed to get flight notifications"}), 500

    @app.route("/api/flights/search", methods=["GET"])
    def search_flights():
        """Search flights by various criteria"""
        try:
            session = SessionLocal()

            # Get search parameters
            departure = request.args.get("departure")
            arrival = request.args.get("arrival")
            airline = request.args.get("airline")
            status = request.args.get("status")

            # Build query
            query = session.query(FlightPlanDBModel)

            if departure:
                query = query.filter(
                    FlightPlanDBModel.departure_airport.ilike(f"%{departure}%")
                )
            if arrival:
                query = query.filter(
                    FlightPlanDBModel.arrival_airport.ilike(f"%{arrival}%")
                )
            if airline:
                query = query.join(AircraftDBModel).filter(
                    AircraftDBModel.airline.ilike(f"%{airline}%")
                )

            flights = query.limit(100).all()

            flight_data = []
            for flight in flights:
                flight_data.append(
                    {
                        "aircraft_id": flight.aircraft_id,
                        "gufi": flight.gufi,
                        "departure_airport": flight.departure_airport,
                        "arrival_airport": flight.arrival_airport,
                        "scheduled_departure": (
                            flight.igtd.isoformat() if flight.igtd else None
                        ),
                        "scheduled_arrival": (
                            flight.eta.isoformat() if flight.eta else None
                        ),
                    }
                )

            session.close()
            return jsonify({"flights": flight_data, "count": len(flight_data)})

        except Exception as e:
            logger.error(f"Error searching flights: {e}", exc_info=True)
            return jsonify({"error": "Failed to search flights"}), 500
