#!/usr/bin/env python3
"""
Route Data Processor - Handles new route data insertion into normalized tables
This should be called whenever new track_information data is received with route data.
"""

import json
from datetime import datetime
from db_config import SessionLocal
from sqlalchemy import text
from utils.logger import main_logger as logger


def process_route_data(
    aircraft_id,
    route_of_flight,
    waypoints,
    fixes=None,
    departure_airport=None,
    arrival_airport=None,
    time_at_position=None,
):
    """
    Process and store route data in normalized tables.

    Args:
        aircraft_id (str): Aircraft identifier
        route_of_flight (str): Filed route string
        waypoints (str|list): Waypoints data (JSON string or list)
        fixes (str|list, optional): Fixes data
        departure_airport (str, optional): Departure airport code
        arrival_airport (str, optional): Arrival airport code
        time_at_position (str, optional): Timestamp for the route data
    """

    if not route_of_flight or not aircraft_id:
        logger.warning(f"Missing required route data for aircraft {aircraft_id}")
        return False

    try:
        session = SessionLocal()

        # Extract date from time_at_position
        try:
            if time_at_position:
                flight_date = datetime.fromisoformat(
                    time_at_position.replace("Z", "+00:00")
                ).date()
            else:
                flight_date = datetime.now().date()
        except:
            flight_date = datetime.now().date()

        # Insert or update flight route
        route_query = text(
            """
            INSERT INTO flight_routes 
            (aircraft_id, flight_date, filed_route, route_text, departure_airport, arrival_airport)
            VALUES (:aircraft_id, :flight_date, :filed_route, :route_text, :dep_airport, :arr_airport)
            ON CONFLICT (aircraft_id, flight_date) 
            DO UPDATE SET
                filed_route = EXCLUDED.filed_route,
                route_text = EXCLUDED.route_text,
                departure_airport = EXCLUDED.departure_airport,
                arrival_airport = EXCLUDED.arrival_airport,
                updated_at = NOW()
            RETURNING id
        """
        )

        result = session.execute(
            route_query,
            {
                "aircraft_id": aircraft_id,
                "flight_date": flight_date,
                "filed_route": route_of_flight,
                "route_text": route_of_flight,
                "dep_airport": departure_airport,
                "arr_airport": arrival_airport,
            },
        )

        route_id = result.fetchone()[0]
        logger.info(f"✅ Processed route for {aircraft_id}: {route_of_flight}")

        # Process waypoints if available
        if waypoints:
            try:
                waypoints_data = (
                    json.loads(waypoints) if isinstance(waypoints, str) else waypoints
                )

                # Clear existing waypoints for this route
                session.execute(
                    text("DELETE FROM route_waypoints WHERE route_id = :route_id"),
                    {"route_id": route_id},
                )

                # Insert new waypoints
                waypoint_count = 0
                for i, waypoint in enumerate(waypoints_data):
                    if isinstance(waypoint, dict):
                        waypoint_query = text(
                            """
                            INSERT INTO route_waypoints 
                            (route_id, sequence_order, waypoint_name, latitude, longitude, altitude, elapsed_time)
                            VALUES (:route_id, :sequence, :name, :lat, :lon, :alt, :elapsed)
                        """
                        )

                        session.execute(
                            waypoint_query,
                            {
                                "route_id": route_id,
                                "sequence": i + 1,
                                "name": waypoint.get("name", f"WP{i+1}"),
                                "lat": (
                                    float(waypoint.get("latitude", 0))
                                    if waypoint.get("latitude")
                                    else None
                                ),
                                "lon": (
                                    float(waypoint.get("longitude", 0))
                                    if waypoint.get("longitude")
                                    else None
                                ),
                                "alt": waypoint.get("altitude"),
                                "elapsed": waypoint.get("elapsed_time"),
                            },
                        )
                        waypoint_count += 1

                logger.info(
                    f"📍 Processed {waypoint_count} waypoints for route {route_id}"
                )

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.error(f"❌ Error processing waypoints for {aircraft_id}: {e}")

        session.commit()
        return True

    except Exception as e:
        logger.error(f"❌ Error processing route data for {aircraft_id}: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_route_summary():
    """Get summary statistics of route data."""
    try:
        session = SessionLocal()

        # Get route counts
        route_count = session.execute(
            text("SELECT COUNT(*) FROM flight_routes")
        ).fetchone()[0]
        waypoint_count = session.execute(
            text("SELECT COUNT(*) FROM route_waypoints")
        ).fetchone()[0]

        # Get recent activity
        recent_routes = session.execute(
            text(
                """
            SELECT COUNT(*) FROM flight_routes 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """
            )
        ).fetchone()[0]

        logger.info(f"📊 Route Data Summary:")
        logger.info(f"   🛩️  Total Routes: {route_count:,}")
        logger.info(f"   📍 Total Waypoints: {waypoint_count:,}")
        logger.info(f"   🆕 Recent Routes (24h): {recent_routes:,}")

        return {
            "total_routes": route_count,
            "total_waypoints": waypoint_count,
            "recent_routes": recent_routes,
        }

    except Exception as e:
        logger.error(f"❌ Error getting route summary: {e}")
        return None
    finally:
        session.close()


if __name__ == "__main__":
    # Test the route processor
    get_route_summary()


