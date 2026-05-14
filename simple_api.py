"""
Simple API endpoints for the frontend - works with existing database structure
"""

import os

from flask import Flask, jsonify, request
from sqlalchemy import text
from utils.logger import main_logger as logger
import json

from db_config import SessionLocal

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _LIMITER_AVAILABLE = True
except ImportError:
    Limiter = None
    get_remote_address = None
    _LIMITER_AVAILABLE = False

# ── API key auth ───────────────────────────────────────────────────────────────
# Set GOLFMIKE_API_KEYS to a comma-separated list of valid bearer tokens.
# If the env var is empty or unset all /v1/ requests are rejected.
_RAW_KEYS = os.getenv("GOLFMIKE_API_KEYS", "")
_VALID_KEYS: set[str] = {k.strip() for k in _RAW_KEYS.split(",") if k.strip()}


def _get_api_key() -> str:
    """Extract API key from X-API-Key header or ?api_key= query param."""
    return (
        request.headers.get("X-API-Key", "")
        or request.args.get("api_key", "")
    )


def create_simple_api(app: Flask) -> None:
    """Add simple flight tracking endpoints to the Flask app"""

    # ── Rate limiter (Redis backend, keyed by API key) ─────────────────────
    if _LIMITER_AVAILABLE:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        limiter = Limiter(
            key_func=lambda: _get_api_key() or get_remote_address(),
            app=app,
            storage_uri=redis_url,
            default_limits=["500/hour", "60/minute"],
            strategy="fixed-window",
        )
    else:
        logger.warning("flask_limiter not installed — rate limiting disabled. Run: pip install flask-limiter")
        # Stub so @limiter.limit() decorators below don't crash
        class _NoopLimiter:
            def limit(self, *a, **kw):
                return lambda f: f
        limiter = _NoopLimiter()

    # ── Auth gate for all /v1/ routes ──────────────────────────────────────
    @app.before_request
    def _require_api_key():
        if not request.path.startswith("/v1/"):
            return None
        if not _VALID_KEYS:
            # No keys configured — open access with a log warning (dev/single-user mode)
            return None
        key = _get_api_key()
        if not key or key not in _VALID_KEYS:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return None

    @app.route("/home", methods=["GET"])
    def home_page():
        from flask import redirect
        return redirect("/", 301)

    @app.route("/search", methods=["GET"])
    def search_page():
        from flask import redirect
        return redirect("/", 301)

    @app.route("/api/client-config", methods=["GET"])
    def client_config():
        """Return the web-UI API key so the frontend can authenticate /v1/ calls."""
        key = next(iter(_VALID_KEYS), None)
        return jsonify({"api_key": key})

    @app.route("/api/autocomplete", methods=["GET"])
    def autocomplete():
        """Provide autocomplete suggestions based on aircraft database"""
        query = request.args.get("q", "").strip().upper()
        limit = request.args.get("limit", "10")

        if not query or len(query) < 2:
            return jsonify([])

        try:
            session = SessionLocal()

            # Search across multiple fields for comprehensive autocomplete
            suggestions = []

            # Search aircraft IDs (tail numbers)
            aircraft_query = text(
                """
                SELECT DISTINCT aircraft_id, 'aircraft' as type, aircraft_id as display_text
                FROM flight_plan 
                WHERE aircraft_id ILIKE :query
                ORDER BY aircraft_id
                LIMIT :limit
            """
            )
            aircraft_results = session.execute(
                aircraft_query, {"query": f"%{query}%", "limit": int(limit)}
            )
            for row in aircraft_results:
                suggestions.append(
                    {
                        "text": row.aircraft_id,
                        "type": "aircraft",
                        "display": f"✈️ {row.aircraft_id}",
                        "category": "Aircraft",
                    }
                )

            # Search departure airports
            dep_query = text(
                """
                SELECT DISTINCT departure_airport, 'departure' as type
                FROM flight_plan 
                WHERE departure_airport ILIKE :query
                ORDER BY departure_airport
                LIMIT :limit
            """
            )
            dep_results = session.execute(
                dep_query, {"query": f"%{query}%", "limit": int(limit)}
            )
            for row in dep_results:
                suggestions.append(
                    {
                        "text": row.departure_airport,
                        "type": "airport",
                        "display": f"🛫 {row.departure_airport}",
                        "category": "Departure Airport",
                    }
                )

            # Search arrival airports
            arr_query = text(
                """
                SELECT DISTINCT arrival_airport, 'arrival' as type
                FROM flight_plan 
                WHERE arrival_airport ILIKE :query
                ORDER BY arrival_airport
                LIMIT :limit
            """
            )
            arr_results = session.execute(
                arr_query, {"query": f"%{query}%", "limit": int(limit)}
            )
            for row in arr_results:
                suggestions.append(
                    {
                        "text": row.arrival_airport,
                        "type": "airport",
                        "display": f"🛬 {row.arrival_airport}",
                        "category": "Arrival Airport",
                    }
                )

            # Search upcoming flights
            upcoming_query = text(
                """
                SELECT DISTINCT aircraft_id, 'upcoming' as type
                FROM upcoming_flights 
                WHERE aircraft_id ILIKE :query
                ORDER BY aircraft_id
                LIMIT :limit
            """
            )
            upcoming_results = session.execute(
                upcoming_query, {"query": f"%{query}%", "limit": int(limit)}
            )
            for row in upcoming_results:
                suggestions.append(
                    {
                        "text": row.aircraft_id,
                        "type": "upcoming",
                        "display": f"📅 {row.aircraft_id}",
                        "category": "Upcoming Flight",
                    }
                )

            session.close()

            # Remove duplicates and limit results
            seen = set()
            unique_suggestions = []
            for suggestion in suggestions:
                key = suggestion["text"]
                if key not in seen:
                    seen.add(key)
                    unique_suggestions.append(suggestion)
                    if len(unique_suggestions) >= int(limit):
                        break

            return jsonify(unique_suggestions)

        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
            return jsonify([])

    @app.route("/api/flights/current", methods=["GET"])
    def get_current_flights():
        """Get all currently active flights"""
        try:
            session = SessionLocal()

            # Enhanced query to get flight plans with latest position data
            query = text(
                """
                SELECT 
                    fp.aircraft_id,
                    fp.gufi,
                    fp.departure_airport,
                    fp.arrival_airport,
                    fp.igtd,
                    ti.latitude,
                    ti.longitude,
                    ti.altitude,
                    ti.speed,
                    ti.time_at_position
                FROM flight_plan fp
                LEFT JOIN (
                    SELECT DISTINCT ON (aircraft_id) 
                        aircraft_id, latitude, longitude, altitude, speed, time_at_position
                    FROM track_information 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                    AND latitude != '' AND longitude != ''
                    ORDER BY aircraft_id, time_at_position DESC
                ) ti ON fp.aircraft_id = ti.aircraft_id
                LIMIT 50
            """
            )

            result = session.execute(query)
            flights = []

            for row in result:
                # Determine flight status based on position data
                has_position = row.latitude is not None and row.longitude is not None
                status = "IN_FLIGHT" if has_position else "PLANNED"

                flight = {
                    "aircraft_id": row.aircraft_id,
                    "gufi": row.gufi,
                    "departure_airport": row.departure_airport,
                    "arrival_airport": row.arrival_airport,
                    "scheduled_departure": row.igtd.isoformat() if row.igtd else None,
                    "scheduled_arrival": None,  # No ETA column in this table
                    "current_status": status,
                    "status_timestamp": (
                        row.time_at_position if row.time_at_position else None
                    ),
                    "position": {
                        "latitude": float(row.latitude) if row.latitude else None,
                        "longitude": float(row.longitude) if row.longitude else None,
                        "altitude": row.altitude,
                        "speed": row.speed,
                        "heading": None,  # Not available in track_information
                        "timestamp": (
                            row.time_at_position if row.time_at_position else None
                        ),
                    },
                }
                flights.append(flight)

            session.close()
            return jsonify({"flights": flights, "count": len(flights)})

        except Exception as e:
            logger.error("Error getting current flights", exc_info=True)
            return jsonify({"error": "Failed to get current flights"}), 500

    @app.route("/api/flights/notifications", methods=["GET"])
    def get_flight_notifications():
        """Get recent flight notifications"""
        try:
            # For now, return empty notifications since status_updates table is empty
            # This will be populated when flight events are processed
            notifications = []
            return jsonify(
                {"notifications": notifications, "count": len(notifications)}
            )

        except Exception as e:
            logger.error("Error getting notifications", exc_info=True)
            return jsonify({"error": "Failed to get notifications"}), 500

    @app.route("/api/flights/search", methods=["GET"])
    def search_flights():
        """Search flights by various criteria"""
        try:
            session = SessionLocal()

            departure = request.args.get("departure")
            arrival = request.args.get("arrival")
            query_param = request.args.get("q", "").strip()

            # If q parameter is provided, do a general search
            if query_param:
                # Search both current flights and upcoming flights
                query = """
                    SELECT DISTINCT
                        uf.aircraft_id,
                        uf.gufi,
                        uf.departure_airport,
                        uf.arrival_airport,
                        uf.departure_time as scheduled_departure,
                        NULL as latitude,
                        NULL as longitude,
                        NULL as altitude,
                        NULL as speed,
                        NULL as time_at_position,
                        'upcoming' as flight_type
                    FROM upcoming_flights uf
                    WHERE (uf.aircraft_id ILIKE :query
                       OR uf.departure_airport ILIKE :query
                       OR uf.arrival_airport ILIKE :query
                       OR uf.gufi ILIKE :query
                       OR uf.flight_reference ILIKE :query)
                    AND uf.departure_time > NOW()
                    AND uf.status IN ('PLANNED', 'ACTIVE')
                    ORDER BY scheduled_departure DESC
                    LIMIT 20
                """
                params = {"query": f"%{query_param}%"}
            else:
                # Original specific search by departure/arrival
                query = "SELECT aircraft_id, gufi, departure_airport, arrival_airport, igtd FROM flight_plan WHERE 1=1"
                params = {}

                if departure:
                    query += " AND departure_airport ILIKE :departure"
                    params["departure"] = f"%{departure}%"

                if arrival:
                    query += " AND arrival_airport ILIKE :arrival"
                    params["arrival"] = f"%{arrival}%"

                query += " LIMIT 100"

            result = session.execute(text(query), params)
            flights = []

            for row in result:
                flight = {
                    "aircraft_id": row.aircraft_id,
                    "gufi": row.gufi,
                    "departure_airport": row.departure_airport,
                    "arrival_airport": row.arrival_airport,
                    "scheduled_departure": (
                        row.scheduled_departure.isoformat()
                        if row.scheduled_departure
                        else None
                    ),
                    "scheduled_arrival": None,  # No ETA column in this table
                }

                # Add flight type if available
                if hasattr(row, "flight_type"):
                    flight["flight_type"] = row.flight_type

                # Add position data if available (when using q parameter)
                if hasattr(row, "latitude") and hasattr(row, "longitude"):
                    if row.latitude and row.longitude:
                        flight["position"] = {
                            "latitude": float(row.latitude) if row.latitude else None,
                            "longitude": (
                                float(row.longitude) if row.longitude else None
                            ),
                            "altitude": row.altitude,
                            "speed": row.speed,
                            "timestamp": row.time_at_position,
                        }

                flights.append(flight)

            # If no results found and we have a query parameter, try searching in track_information
            if len(flights) == 0 and query_param:
                fallback_query = """
                    SELECT DISTINCT
                        aircraft_id,
                        NULL as gufi,
                        NULL as departure_airport,
                        NULL as arrival_airport,
                        NULL as igtd,
                        latitude,
                        longitude,
                        altitude,
                        speed,
                        time_at_position
                    FROM track_information 
                    WHERE aircraft_id ILIKE :query
                    AND latitude IS NOT NULL AND longitude IS NOT NULL
                    AND latitude != '' AND longitude != ''
                    ORDER BY time_at_position DESC
                    LIMIT 20
                """
                fallback_result = session.execute(
                    text(fallback_query), {"query": f"%{query_param}%"}
                )

                for row in fallback_result:
                    flight = {
                        "aircraft_id": row.aircraft_id,
                        "gufi": row.gufi,
                        "departure_airport": row.departure_airport,
                        "arrival_airport": row.arrival_airport,
                        "scheduled_departure": (
                            row.igtd.isoformat() if row.igtd else None
                        ),
                        "scheduled_arrival": None,
                    }

                    # Add position data
                    if row.latitude and row.longitude:
                        flight["position"] = {
                            "latitude": float(row.latitude) if row.latitude else None,
                            "longitude": (
                                float(row.longitude) if row.longitude else None
                            ),
                            "altitude": row.altitude,
                            "speed": row.speed,
                            "timestamp": row.time_at_position,
                        }

                    flights.append(flight)

            session.close()

            # Return different response format based on search type
            if query_param:
                return jsonify(
                    {"query": query_param, "count": len(flights), "flights": flights}
                )
            else:
                return jsonify({"flights": flights, "count": len(flights)})

        except Exception as e:
            logger.error("Error searching flights", exc_info=True)
            return jsonify({"error": "Failed to search flights"}), 500

    @app.route("/api/flights/<aircraft_id>/position", methods=["GET"])
    def get_aircraft_position(aircraft_id: str):
        """Get current position of a specific aircraft"""
        try:
            session = SessionLocal()

            query = text(
                """
                SELECT 
                    aircraft_id,
                    latitude,
                    longitude,
                    altitude,
                    speed,
                    time_at_position
                FROM track_information 
                WHERE aircraft_id = :aircraft_id 
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
                AND latitude != ''
                AND longitude != ''
                ORDER BY time_at_position DESC 
                LIMIT 1
            """
            )

            result = session.execute(query, {"aircraft_id": aircraft_id})
            row = result.fetchone()

            if not row:
                session.close()
                return jsonify({"error": "Aircraft not found or no position data"}), 404

            position = {
                "aircraft_id": row.aircraft_id,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "altitude": row.altitude,
                "speed": row.speed,
                "timestamp": row.time_at_position if row.time_at_position else None,
            }

            session.close()
            return jsonify(position)

        except Exception as e:
            logger.error("Error getting aircraft position", exc_info=True)
            return jsonify({"error": "Failed to get aircraft position"}), 500

    @app.route("/api/flights/<aircraft_id>/track", methods=["GET"])
    def get_aircraft_track(aircraft_id: str):
        """Get track history for a specific aircraft"""
        try:
            session = SessionLocal()

            hours_back = request.args.get("hours", 24, type=int)

            query = text(
                """
                SELECT 
                    latitude,
                    longitude,
                    altitude,
                    speed,
                    time_at_position
                FROM track_information 
                WHERE aircraft_id = :aircraft_id 
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
                AND latitude != ''
                AND longitude != ''
                ORDER BY time_at_position DESC
                LIMIT 100
            """
            )

            result = session.execute(query, {"aircraft_id": aircraft_id})
            tracks = []

            for row in result:
                track = {
                    "latitude": float(row.latitude),
                    "longitude": float(row.longitude),
                    "altitude": row.altitude,
                    "speed": row.speed,
                    "timestamp": row.time_at_position if row.time_at_position else None,
                }
                tracks.append(track)

            session.close()
            return jsonify(
                {"aircraft_id": aircraft_id, "tracks": tracks, "count": len(tracks)}
            )

        except Exception as e:
            logger.error("Error getting aircraft track", exc_info=True)
            return jsonify({"error": "Failed to get aircraft track"}), 500

    @app.route("/api/flights/<aircraft_id>/flightplan", methods=["GET"])
    def get_flight_plan(aircraft_id):
        """Get flight plan with waypoints for a specific aircraft"""
        try:
            session = SessionLocal()
            # Get the most recent flight plan and track data
            # First try to get from flight_plan table with waypoints
            query = text(
                """
                SELECT 
                    fp.aircraft_id,
                    fp.gufi,
                    fp.departure_airport,
                    fp.arrival_airport,
                    fp.igtd,
                    fp.\"flightPlanRoute_10a\" as route_text,
                    ti.waypoints,
                    ti.fixes,
                    ti.route_of_flight,
                    ti.time_at_position
                FROM flight_plan fp
                LEFT JOIN (
                    SELECT DISTINCT ON (aircraft_id) 
                        aircraft_id, waypoints, fixes, route_of_flight, time_at_position
                    FROM track_information 
                    WHERE aircraft_id = :aircraft_id
                    AND waypoints IS NOT NULL
                    ORDER BY aircraft_id, time_at_position DESC
                ) ti ON fp.aircraft_id = ti.aircraft_id
                WHERE fp.aircraft_id = :aircraft_id
                ORDER BY fp.igtd DESC
                LIMIT 1
                """
            )

            result = session.execute(query, {"aircraft_id": aircraft_id})
            row = result.fetchone()

            # If no flight plan found, try to get data from track_information only
            if not row:
                fallback_query = text(
                    """
                    SELECT 
                        aircraft_id,
                        NULL as gufi,
                        NULL as departure_airport,
                        NULL as arrival_airport,
                        NULL as igtd,
                        NULL as route_text,
                        waypoints,
                        fixes,
                        route_of_flight,
                        time_at_position
                    FROM track_information 
                    WHERE aircraft_id = :aircraft_id
                    AND waypoints IS NOT NULL
                    ORDER BY time_at_position DESC
                    LIMIT 1
                    """
                )
                result = session.execute(fallback_query, {"aircraft_id": aircraft_id})
                row = result.fetchone()

                if not row:
                    session.close()
                    return jsonify({"error": "Flight plan not found"}), 404

            # Parse waypoints if they exist
            waypoints = []
            if row.waypoints:
                try:
                    import json

                    waypoints = (
                        json.loads(row.waypoints)
                        if isinstance(row.waypoints, str)
                        else row.waypoints
                    )
                except:
                    waypoints = []

            # Parse fixes if they exist
            fixes = []
            if row.fixes:
                try:
                    import json

                    fixes = (
                        json.loads(row.fixes)
                        if isinstance(row.fixes, str)
                        else row.fixes
                    )
                except:
                    fixes = []

            flight_plan = {
                "aircraft_id": row.aircraft_id,
                "gufi": row.gufi,
                "departure_airport": row.departure_airport,
                "arrival_airport": row.arrival_airport,
                "scheduled_departure": row.igtd.isoformat() if row.igtd else None,
                "route_text": row.route_text,
                "route_of_flight": row.route_of_flight,
                "waypoints": waypoints,
                "fixes": fixes,
                "waypoint_count": len(waypoints),
                "fix_count": len(fixes),
                "last_updated": row.time_at_position,
            }

            session.close()
            return jsonify(flight_plan)

        except Exception as e:
            logger.error("Error getting flight plan: " + str(e))
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/flights/<aircraft_id>/detail", methods=["GET"])
    def get_flight_detail(aircraft_id):
        """Get comprehensive flight detail data for a specific aircraft and date"""
        try:
            session = SessionLocal()
            date = request.args.get("date", "")

            # Get flight plan data
            flight_query = text(
                """
                SELECT 
                    fp.aircraft_id,
                    fp.gufi,
                    fp.departure_airport,
                    fp.arrival_airport,
                    fp.igtd,
                    fp."flightPlanRoute_10a" as route_text
                FROM flight_plan fp
                WHERE fp.aircraft_id = :aircraft_id
                ORDER BY fp.igtd DESC
                LIMIT 1
                """
            )

            result = session.execute(flight_query, {"aircraft_id": aircraft_id})
            flight_row = result.fetchone()

            # If no flight plan found, create a basic flight row from track data
            if not flight_row:
                # Get basic info from track_information
                track_query = text(
                    """
                    SELECT 
                        aircraft_id,
                        NULL as gufi,
                        NULL as departure_airport,
                        NULL as arrival_airport,
                        NULL as igtd,
                        NULL as route_text
                    FROM track_information 
                    WHERE aircraft_id = :aircraft_id
                    ORDER BY time_at_position DESC
                    LIMIT 1
                """
                )
                result = session.execute(track_query, {"aircraft_id": aircraft_id})
                flight_row = result.fetchone()

                if not flight_row:
                    session.close()
                    return jsonify({"error": "Aircraft not found"}), 404

            # Get route data from track_information table (fallback since flight_routes doesn't exist yet)
            route_query = text(
                """
                SELECT 
                    NULL as route_id,
                    route_of_flight as filed_route,
                    route_of_flight as route_text,
                    departure_airport,
                    arrival_airport
                FROM track_information 
                WHERE aircraft_id = :aircraft_id
                AND route_of_flight IS NOT NULL
                ORDER BY time_at_position DESC
                LIMIT 1
                """
            )

            route_result = session.execute(route_query, {"aircraft_id": aircraft_id})
            route_row = route_result.fetchone()

            # Get waypoints from track_information table (fallback since route_waypoints doesn't exist yet)
            waypoints_query = text(
                """
                SELECT 
                    'WP' as waypoint_name,
                    latitude,
                    longitude,
                    altitude,
                    NULL as elapsed_time,
                    ROW_NUMBER() OVER (ORDER BY time_at_position) as sequence_order
                FROM track_information 
                WHERE aircraft_id = :aircraft_id
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
                ORDER BY time_at_position ASC
                LIMIT 20
                """
            )

            waypoints_data = []
            waypoints_result = session.execute(
                waypoints_query, {"aircraft_id": aircraft_id}
            )
            waypoints_data = waypoints_result.fetchall()

            # Get track data for the flight
            track_query = text(
                """
                SELECT 
                    time_at_position,
                    latitude,
                    longitude,
                    altitude,
                    speed
                FROM track_information 
                WHERE aircraft_id = :aircraft_id
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL 
                AND latitude != '' 
                AND longitude != ''
                ORDER BY time_at_position ASC
                """
            )

            track_result = session.execute(track_query, {"aircraft_id": aircraft_id})
            track_rows = track_result.fetchall()

            # Get OOOI data (Out, Off, On, In times)
            oooi_query = text(
                """
                SELECT 
                    MIN(CASE WHEN "statusType" = 'OUT' THEN time END) as out_time,
                    MIN(CASE WHEN "statusType" = 'OFF' THEN time END) as off_time,
                    MIN(CASE WHEN "statusType" = 'ON' THEN time END) as on_time,
                    MIN(CASE WHEN "statusType" = 'IN' THEN time END) as in_time
                FROM status_updates 
                WHERE aircraft_id = :aircraft_id
                """
            )

            oooi_result = session.execute(oooi_query, {"aircraft_id": aircraft_id})
            oooi_row = oooi_result.fetchone()

            # Get aircraft details (fallback since aircraft table doesn't exist yet)
            aircraft_query = text(
                """
                SELECT 
                    aircraft_id,
                    'Unknown' as airline,
                    'General Aviation' as aircraft_category,
                    'Private' as user_category
                FROM track_information 
                WHERE aircraft_id = :aircraft_id
                LIMIT 1
                """
            )

            aircraft_result = session.execute(
                aircraft_query, {"aircraft_id": aircraft_id}
            )
            aircraft_row = aircraft_result.fetchone()

            # Get weather data for departure and arrival airports
            weather_data = {
                "departure_metar": None,
                "arrival_metar": None,
                "departure_taf": None,
                "arrival_taf": None,
                "weather_alerts": [],
            }

            logger.info(f"Flight row: {flight_row}")
            if flight_row:
                logger.info(
                    f"Flight airports: {flight_row.departure_airport} -> {flight_row.arrival_airport}"
                )

            # Convert IATA codes to ICAO codes for weather lookup
            def iata_to_icao(airport_code):
                """Convert 3-letter IATA code to 4-letter ICAO code, or return ICAO code as-is"""
                if not airport_code:
                    return airport_code

                airport_code = airport_code.upper()

                # If it's already a 4-letter ICAO code, return as-is
                if len(airport_code) == 4:
                    return airport_code

                # If it's a 3-letter IATA code, convert to ICAO
                if len(airport_code) == 3:
                    # Common IATA to ICAO conversions
                    iata_to_icao_map = {
                        "YYC": "CYYC",  # Calgary
                        "TPA": "KTPA",  # Tampa
                        "PHX": "KPHX",  # Phoenix
                        "JFK": "KJFK",  # New York JFK
                        "DTW": "KDTW",  # Detroit
                        "BOS": "KBOS",  # Boston
                        "BWI": "KBWI",  # Baltimore
                        "CHS": "KCHS",  # Charleston
                        "HPN": "KHPN",  # White Plains
                        "YUL": "CYUL",  # Montreal
                        "BDL": "KBDL",  # Hartford
                        "DEN": "KDEN",  # Denver
                        "RDU": "KRDU",  # Raleigh-Durham
                        "GRR": "KGRR",  # Grand Rapids
                        "PVD": "KPVD",  # Providence
                    }
                    return iata_to_icao_map.get(airport_code, f"K{airport_code}")

                # Return as-is for any other format
                return airport_code

            # Get METAR data for departure and arrival airports
            if (
                flight_row
                and flight_row.departure_airport
                and flight_row.arrival_airport
            ):
                # Convert to ICAO codes
                departure_icao = iata_to_icao(flight_row.departure_airport)
                arrival_icao = iata_to_icao(flight_row.arrival_airport)

                logger.info(
                    f"Fetching weather for {flight_row.departure_airport} ({departure_icao}) -> {flight_row.arrival_airport} ({arrival_icao})"
                )

                # Check which airports have METAR data available
                available_airports = []
                for airport, icao_code in [
                    (flight_row.departure_airport, departure_icao),
                    (flight_row.arrival_airport, arrival_icao),
                ]:
                    try:
                        check_query = text(
                            "SELECT COUNT(*) FROM metar_data_api WHERE station_id = :station_id"
                        )
                        result = session.execute(check_query, {"station_id": icao_code})
                        count = result.scalar()
                        if count > 0:
                            available_airports.append((airport, icao_code))
                            logger.info(
                                f"✅ METAR data available for {airport} ({icao_code})"
                            )
                        else:
                            logger.info(f"❌ No METAR data for {airport} ({icao_code})")
                    except Exception as e:
                        logger.error(
                            f"Error checking METAR for {airport} ({icao_code}): {e}"
                        )

                if available_airports:
                    try:
                        # Get METAR for departure airport
                        departure_airport_available = any(
                            airport == flight_row.departure_airport
                            for airport, _ in available_airports
                        )
                        if departure_airport_available:
                            departure_metar_query = text(
                                """
                                SELECT 
                                    station_id,
                                    observation_time,
                                    raw_text,
                                    temperature,
                                    dewpoint,
                                    wind_direction,
                                    wind_speed,
                                    visibility,
                                    flight_category,
                                    sky_conditions,
                                    weather_phenomena
                                FROM metar_data_api 
                                WHERE station_id = :station_id
                                ORDER BY observation_time DESC
                                LIMIT 1
                                """
                            )

                            departure_metar_result = session.execute(
                                departure_metar_query,
                                {"station_id": departure_icao},
                            )
                            departure_metar = departure_metar_result.fetchone()

                            if departure_metar:
                                # Convert Celsius to Fahrenheit
                                temp_c = departure_metar.temperature
                                temp_f = (
                                    round((temp_c * 9 / 5) + 32, 1)
                                    if temp_c is not None
                                    else None
                                )

                                dewpoint_c = departure_metar.dewpoint
                                dewpoint_f = (
                                    round((dewpoint_c * 9 / 5) + 32, 1)
                                    if dewpoint_c is not None
                                    else None
                                )

                                weather_data["departure_metar"] = {
                                    "station_id": departure_metar.station_id,
                                    "observation_time": (
                                        departure_metar.observation_time.isoformat()
                                        if departure_metar.observation_time
                                        else None
                                    ),
                                    "raw_text": departure_metar.raw_text,
                                    "temperature": {
                                        "celsius": temp_c,
                                        "fahrenheit": temp_f,
                                    },
                                    "dewpoint": {
                                        "celsius": dewpoint_c,
                                        "fahrenheit": dewpoint_f,
                                    },
                                    "wind_direction": departure_metar.wind_direction,
                                    "wind_speed": departure_metar.wind_speed,
                                    "visibility": departure_metar.visibility,
                                    "flight_category": departure_metar.flight_category,
                                    "sky_conditions": departure_metar.sky_conditions,
                                    "weather_phenomena": departure_metar.weather_phenomena,
                                }

                        # Get METAR for arrival airport
                        arrival_airport_available = any(
                            airport == flight_row.arrival_airport
                            for airport, _ in available_airports
                        )
                        if arrival_airport_available:
                            arrival_metar_query = text(
                                """
                                SELECT 
                                    station_id,
                                    observation_time,
                                    raw_text,
                                    temperature,
                                    dewpoint,
                                    wind_direction,
                                    wind_speed,
                                    visibility,
                                    flight_category,
                                    sky_conditions,
                                    weather_phenomena
                                FROM metar_data_api 
                                WHERE station_id = :station_id
                                ORDER BY observation_time DESC
                                LIMIT 1
                                """
                            )

                            arrival_metar_result = session.execute(
                                arrival_metar_query,
                                {"station_id": arrival_icao},
                            )
                            arrival_metar = arrival_metar_result.fetchone()

                            if arrival_metar:
                                # Convert Celsius to Fahrenheit
                                temp_c = arrival_metar.temperature
                                temp_f = (
                                    round((temp_c * 9 / 5) + 32, 1)
                                    if temp_c is not None
                                    else None
                                )

                                dewpoint_c = arrival_metar.dewpoint
                                dewpoint_f = (
                                    round((dewpoint_c * 9 / 5) + 32, 1)
                                    if dewpoint_c is not None
                                    else None
                                )

                                weather_data["arrival_metar"] = {
                                    "station_id": arrival_metar.station_id,
                                    "observation_time": (
                                        arrival_metar.observation_time.isoformat()
                                        if arrival_metar.observation_time
                                        else None
                                    ),
                                    "raw_text": arrival_metar.raw_text,
                                    "temperature": {
                                        "celsius": temp_c,
                                        "fahrenheit": temp_f,
                                    },
                                    "dewpoint": {
                                        "celsius": dewpoint_c,
                                        "fahrenheit": dewpoint_f,
                                    },
                                    "wind_direction": arrival_metar.wind_direction,
                                    "wind_speed": arrival_metar.wind_speed,
                                    "visibility": arrival_metar.visibility,
                                    "flight_category": arrival_metar.flight_category,
                                    "sky_conditions": arrival_metar.sky_conditions,
                                    "weather_phenomena": arrival_metar.weather_phenomena,
                                }

                        # Get TAF for departure airport
                        if departure_airport_available:
                            departure_taf_query = text(
                                """
                                SELECT 
                                    station_id,
                                    issue_time,
                                    valid_from,
                                    valid_to,
                                    raw_text,
                                    forecast_periods
                                FROM taf_data_api 
                                WHERE station_id = :station_id
                                ORDER BY issue_time DESC
                                LIMIT 1
                                """
                            )

                            departure_taf_result = session.execute(
                                departure_taf_query,
                                {"station_id": departure_icao},
                            )
                            departure_taf = departure_taf_result.fetchone()

                            if departure_taf:
                                weather_data["departure_taf"] = {
                                    "station_id": departure_taf.station_id,
                                    "issue_time": (
                                        departure_taf.issue_time.isoformat()
                                        if departure_taf.issue_time
                                        else None
                                    ),
                                    "valid_from": (
                                        departure_taf.valid_from.isoformat()
                                        if departure_taf.valid_from
                                        else None
                                    ),
                                    "valid_to": (
                                        departure_taf.valid_to.isoformat()
                                        if departure_taf.valid_to
                                        else None
                                    ),
                                    "raw_text": departure_taf.raw_text,
                                    "forecast_periods": departure_taf.forecast_periods,
                                }

                        # Get TAF for arrival airport
                        if arrival_airport_available:
                            arrival_taf_query = text(
                                """
                                SELECT 
                                    station_id,
                                    issue_time,
                                    valid_from,
                                    valid_to,
                                    raw_text,
                                    forecast_periods
                                FROM taf_data_api 
                                WHERE station_id = :station_id
                                ORDER BY issue_time DESC
                                LIMIT 1
                                """
                            )

                            arrival_taf_result = session.execute(
                                arrival_taf_query,
                                {"station_id": arrival_icao},
                            )
                            arrival_taf = arrival_taf_result.fetchone()

                            if arrival_taf:
                                weather_data["arrival_taf"] = {
                                    "station_id": arrival_taf.station_id,
                                    "issue_time": (
                                        arrival_taf.issue_time.isoformat()
                                        if arrival_taf.issue_time
                                        else None
                                    ),
                                    "valid_from": (
                                        arrival_taf.valid_from.isoformat()
                                        if arrival_taf.valid_from
                                        else None
                                    ),
                                    "valid_to": (
                                        arrival_taf.valid_to.isoformat()
                                        if arrival_taf.valid_to
                                        else None
                                    ),
                                    "raw_text": arrival_taf.raw_text,
                                    "forecast_periods": arrival_taf.forecast_periods,
                                }

                    except Exception as e:
                        # If METAR/TAF queries fail, just continue with alerts
                        logger.error(f"Weather query error: {e}")
                        pass

            # Get weather alerts from existing tables
            try:
                # Get weather alerts from weather_alerts_api table
                alerts_query = text(
                    """
                    SELECT 
                        alert_id,
                        alert_type,
                        severity,
                        urgency,
                        valid_from,
                        valid_until,
                        summary,
                        description,
                        affected_area,
                        'API' as source
                    FROM weather_alerts_api 
                    WHERE is_active = true 
                    AND (valid_until IS NULL OR valid_until > NOW())
                    ORDER BY issued_at DESC
                    LIMIT 10
                """
                )

                alerts_result = session.execute(alerts_query)
                api_alerts = alerts_result.fetchall()

                # Get weather alerts from weather_alerts table (ITWS)
                itws_alerts_query = text(
                    """
                    SELECT 
                        alert_id,
                        alert_type,
                        severity,
                        urgency,
                        valid_from,
                        valid_until,
                        summary,
                        description,
                        affected_area,
                        'ITWS' as source
                    FROM weather_alerts 
                    WHERE is_active = true 
                    AND (valid_until IS NULL OR valid_until > NOW())
                    AND alert_type LIKE 'ITWS_%'
                    ORDER BY issued_at DESC
                    LIMIT 10
                """
                )

                itws_alerts_result = session.execute(itws_alerts_query)
                itws_alerts = itws_alerts_result.fetchall()

                # Combine alerts
                all_alerts = api_alerts + itws_alerts

                weather_data["weather_alerts"] = [
                    {
                        "alert_id": alert.alert_id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "urgency": alert.urgency,
                        "valid_from": (
                            alert.valid_from.isoformat() if alert.valid_from else None
                        ),
                        "valid_until": (
                            alert.valid_until.isoformat() if alert.valid_until else None
                        ),
                        "summary": alert.summary,
                        "description": alert.description,
                        "affected_area": alert.affected_area,
                        "source": alert.source,
                    }
                    for alert in all_alerts
                ]

            except Exception as e:
                # If weather queries fail, just return empty alerts
                weather_data["weather_alerts"] = []

            # Build response
            flight_data = {
                "flight": {
                    "aircraft_id": aircraft_id,
                    "gufi": flight_row.gufi if flight_row else None,
                    "departure_airport": (
                        flight_row.departure_airport if flight_row else None
                    ),
                    "arrival_airport": (
                        flight_row.arrival_airport if flight_row else None
                    ),
                    "departure_time": (
                        flight_row.igtd.isoformat()
                        if flight_row and flight_row.igtd
                        else None
                    ),
                    "route_text": route_row.route_text if route_row else None,
                    "filed_route": route_row.filed_route if route_row else None,
                    "waypoints": (
                        [
                            {
                                "name": wp.waypoint_name,
                                "latitude": float(wp.latitude) if wp.latitude else None,
                                "longitude": (
                                    float(wp.longitude) if wp.longitude else None
                                ),
                                "altitude": wp.altitude,
                                "elapsed_time": wp.elapsed_time,
                                "sequence": wp.sequence_order,
                            }
                            for wp in waypoints_data
                        ]
                        if waypoints_data
                        else []
                    ),
                    "fixes": [],  # Not available in new structure yet
                    "flight_type": "General Aviation",  # Default
                },
                "track": [
                    {
                        "time": row.time_at_position if row.time_at_position else None,
                        "latitude": float(row.latitude) if row.latitude else None,
                        "longitude": float(row.longitude) if row.longitude else None,
                        "altitude": row.altitude,
                        "ground_speed": row.speed,
                        "heading": None,  # Not available in track_information
                        "remark": "",
                    }
                    for row in track_rows
                ],
                "oooi": {
                    "out_time": (
                        oooi_row.out_time.isoformat()
                        if oooi_row and oooi_row.out_time
                        else None
                    ),
                    "off_time": (
                        oooi_row.off_time.isoformat()
                        if oooi_row and oooi_row.off_time
                        else None
                    ),
                    "on_time": (
                        oooi_row.on_time.isoformat()
                        if oooi_row and oooi_row.on_time
                        else None
                    ),
                    "in_time": (
                        oooi_row.in_time.isoformat()
                        if oooi_row and oooi_row.in_time
                        else None
                    ),
                    "block_time": None,  # Calculate if needed
                },
                "aircraft": {
                    "registration": aircraft_id,
                    "type": (
                        aircraft_row.aircraft_category if aircraft_row else "Unknown"
                    ),
                    "equipment": "ADS-B Out",  # Default since not in aircraft table
                    "owner": aircraft_row.airline if aircraft_row else "Private",
                },
                "timeline": [],  # Will be populated based on OOOI data
                "weather": weather_data,
            }

            # Build comprehensive timeline from multiple data sources
            timeline = []

            # Add OOOI events
            if oooi_row:
                if oooi_row.out_time:
                    timeline.append(
                        {
                            "time": oooi_row.out_time.isoformat(),
                            "title": "OUT — Pushback",
                            "description": "Aircraft pushed back from gate",
                            "badge_class": "bg-primary",
                            "type": "operational",
                        }
                    )
                if oooi_row.off_time:
                    timeline.append(
                        {
                            "time": oooi_row.off_time.isoformat(),
                            "title": "OFF — Takeoff",
                            "description": f"Aircraft airborne from {flight_data.get('departure_airport', 'departure airport')}",
                            "badge_class": "bg-success",
                            "type": "operational",
                        }
                    )
                if oooi_row.on_time:
                    timeline.append(
                        {
                            "time": oooi_row.on_time.isoformat(),
                            "title": "ON — Landing",
                            "description": f"Aircraft landed at {flight_data.get('arrival_airport', 'arrival airport')}",
                            "badge_class": "bg-warning",
                            "type": "operational",
                        }
                    )
                if oooi_row.in_time:
                    timeline.append(
                        {
                            "time": oooi_row.in_time.isoformat(),
                            "title": "IN — At Block",
                            "description": "Aircraft at gate/stand",
                            "badge_class": "bg-secondary",
                            "type": "operational",
                        }
                    )

            # Add significant track events (altitude changes, speed changes)
            if track_rows and len(track_rows) > 1:
                prev_point = None
                takeoff_detected = False
                landing_detected = False

                for i, point in enumerate(track_rows):
                    if prev_point and point.time_at_position:
                        # Check for takeoff (rapid altitude increase from low altitude)
                        if (
                            not takeoff_detected
                            and point.altitude
                            and prev_point.altitude
                            and prev_point.altitude < 1000  # Starting from low altitude
                            and point.altitude > 3000  # Rapid climb
                            and (point.altitude - prev_point.altitude)
                            > 2000  # Significant climb
                        ):
                            takeoff_detected = True
                            time_str = (
                                point.time_at_position.isoformat()
                                if hasattr(point.time_at_position, "isoformat")
                                else str(point.time_at_position)
                            )
                            timeline.append(
                                {
                                    "time": time_str,
                                    "title": "Takeoff Detected",
                                    "description": f"Aircraft climbing to {point.altitude:,} ft",
                                    "badge_class": "bg-success",
                                    "type": "flight",
                                }
                            )

                        # Check for landing (rapid altitude decrease to low altitude)
                        elif (
                            not landing_detected
                            and point.altitude
                            and prev_point.altitude
                            and prev_point.altitude
                            > 3000  # Starting from high altitude
                            and point.altitude < 1000  # Rapid descent
                            and (prev_point.altitude - point.altitude)
                            > 2000  # Significant descent
                        ):
                            landing_detected = True
                            time_str = (
                                point.time_at_position.isoformat()
                                if hasattr(point.time_at_position, "isoformat")
                                else str(point.time_at_position)
                            )
                            timeline.append(
                                {
                                    "time": time_str,
                                    "title": "Landing Detected",
                                    "description": f"Aircraft descending to {point.altitude:,} ft",
                                    "badge_class": "bg-warning",
                                    "type": "flight",
                                }
                            )

                        # Check for significant altitude changes (>5000 ft)
                        elif (
                            point.altitude
                            and prev_point.altitude
                            and abs(point.altitude - prev_point.altitude) > 5000
                        ):
                            # Handle both datetime objects and strings
                            time_str = (
                                point.time_at_position.isoformat()
                                if hasattr(point.time_at_position, "isoformat")
                                else str(point.time_at_position)
                            )
                            timeline.append(
                                {
                                    "time": time_str,
                                    "title": f"Altitude Change — {point.altitude:,} ft",
                                    "description": f"Climb/descent from {prev_point.altitude:,} ft",
                                    "badge_class": "bg-info",
                                    "type": "flight",
                                }
                            )

                        # Check for significant speed changes (>100 kts)
                        if (
                            point.speed
                            and prev_point.speed
                            and abs(point.speed - prev_point.speed) > 100
                        ):
                            # Handle both datetime objects and strings
                            time_str = (
                                point.time_at_position.isoformat()
                                if hasattr(point.time_at_position, "isoformat")
                                else str(point.time_at_position)
                            )
                            timeline.append(
                                {
                                    "time": time_str,
                                    "title": f"Speed Change — {point.speed} kts",
                                    "description": f"Speed change from {prev_point.speed} kts",
                                    "badge_class": "bg-info",
                                    "type": "flight",
                                }
                            )

                    prev_point = point

            # Add weather alert events (deduplicate by time and type)
            if weather_data.get("weather_alerts"):
                seen_alerts = set()
                for alert in weather_data["weather_alerts"]:
                    if alert.get("valid_from"):
                        alert_key = f"{alert['valid_from']}_{alert.get('alert_type', 'Unknown')}"
                        if alert_key not in seen_alerts:
                            seen_alerts.add(alert_key)
                            timeline.append(
                                {
                                    "time": alert["valid_from"],
                                    "title": f"Weather Alert — {alert.get('alert_type', 'Unknown')}",
                                    "description": alert.get(
                                        "summary", "Weather alert issued"
                                    ),
                                    "badge_class": (
                                        "bg-warning"
                                        if alert.get("severity") == "MODERATE"
                                        else "bg-danger"
                                    ),
                                    "type": "weather",
                                }
                            )

            # Add flight plan events
            if flight_row and flight_row.igtd:
                timeline.append(
                    {
                        "time": flight_row.igtd.isoformat(),
                        "title": "Flight Plan Filed",
                        "description": f"Route: {flight_row.departure_airport} → {flight_row.arrival_airport}",
                        "badge_class": "bg-secondary",
                        "type": "planning",
                    }
                )

            # Sort timeline by time
            timeline.sort(key=lambda x: x["time"])

            flight_data["timeline"] = timeline

            session.close()
            return jsonify(flight_data)

        except Exception as e:
            logger.error("Error getting flight detail: " + str(e))
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/flights/<aircraft_id>/recent", methods=["GET"])
    def get_recent_flights(aircraft_id):
        """Get recent flights for an aircraft"""
        try:
            session = SessionLocal()

            # Get recent flights from flight_plan table
            query = text(
                """
                SELECT 
                    aircraft_id,
                    departure_airport,
                    arrival_airport,
                    igtd,
                    DATE(igtd) as flight_date
                FROM flight_plan 
                WHERE aircraft_id = :aircraft_id
                AND igtd IS NOT NULL
                ORDER BY igtd DESC
                LIMIT 10
                """
            )

            result = session.execute(query, {"aircraft_id": aircraft_id})
            rows = result.fetchall()

            recent_flights = [
                {
                    "date": (
                        row.flight_date.strftime("%d %b")
                        if row.flight_date
                        else "Unknown"
                    ),
                    "route": f"{row.departure_airport or 'UNKN'} → {row.arrival_airport or 'UNKN'}",
                    "departure_time": row.igtd.isoformat() if row.igtd else None,
                }
                for row in rows
            ]

            session.close()
            return jsonify(recent_flights)

        except Exception as e:
            logger.error("Error getting recent flights: " + str(e))
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/flights/<aircraft_id>/upcoming", methods=["GET"])
    def get_upcoming_flights(aircraft_id):
        """Get upcoming flights for an aircraft"""
        try:
            session = SessionLocal()

            # Query upcoming flights from the upcoming_flights table
            query = text(
                """
                SELECT 
                    aircraft_id,
                    gufi,
                    flight_reference,
                    departure_airport,
                    arrival_airport,
                    departure_time,
                    arrival_time,
                    aircraft_type,
                    aircraft_operator,
                    route_text,
                    status,
                    source_facility,
                    created_at
                FROM upcoming_flights 
                WHERE aircraft_id = :aircraft_id 
                AND departure_time > NOW()
                AND status IN ('PLANNED', 'ACTIVE')
                ORDER BY departure_time ASC
                LIMIT 10
            """
            )

            result = session.execute(query, {"aircraft_id": aircraft_id.upper()})
            rows = result.fetchall()

            upcoming_flights = [
                {
                    "gufi": row.gufi,
                    "flight_reference": row.flight_reference,
                    "departure_airport": row.departure_airport,
                    "arrival_airport": row.arrival_airport,
                    "departure_time": (
                        row.departure_time.isoformat() if row.departure_time else None
                    ),
                    "arrival_time": (
                        row.arrival_time.isoformat() if row.arrival_time else None
                    ),
                    "aircraft_type": row.aircraft_type,
                    "aircraft_operator": row.aircraft_operator,
                    "route_text": row.route_text,
                    "status": row.status,
                    "source_facility": row.source_facility,
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                }
                for row in rows
            ]

            session.close()
            return jsonify(upcoming_flights)

        except Exception as e:
            logger.error("Error getting upcoming flights: " + str(e))

    # ── Route overlay & events ────────────────────────────────────────────────

    @app.route("/v1/flights/<gufi>/route-overlay", methods=["GET"])
    def route_overlay(gufi: str):
        """
        Return the planned route, actual track, and deviation records for a
        flight so the map can draw both paths and highlight off-route segments.

        Query params:
          hours  – how many hours of track history to include (default 12)
        """
        hours = int(request.args.get("hours", 12))

        try:
            session = SessionLocal()

            # ── Planned waypoints ─────────────────────────────────────────────
            planned_rows = session.execute(
                text(
                    """
                    SELECT sequence, fix_name, latitude, longitude,
                           altitude_restriction, speed_restriction,
                           estimated_time_over, route_source
                    FROM planned_waypoints
                    WHERE gufi = :gufi
                    ORDER BY sequence
                    """
                ),
                {"gufi": gufi},
            ).fetchall()

            planned_route = [
                {
                    "sequence": r.sequence,
                    "fix_name": r.fix_name,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "altitude_restriction": r.altitude_restriction,
                    "speed_restriction": r.speed_restriction,
                    "estimated_time_over": (
                        r.estimated_time_over.isoformat()
                        if r.estimated_time_over
                        else None
                    ),
                    "route_source": r.route_source,
                }
                for r in planned_rows
                if r.latitude is not None and r.longitude is not None
            ]

            # ── Actual track ──────────────────────────────────────────────────
            track_rows = session.execute(
                text(
                    """
                    SELECT latitude, longitude, altitude, speed, heading,
                           time_at_position
                    FROM track_updates
                    WHERE gufi = :gufi
                      AND time_at_position >= NOW() - INTERVAL ':hours hours'
                    ORDER BY time_at_position ASC
                    """.replace(":hours hours", f"{hours} hours")
                ),
                {"gufi": gufi},
            ).fetchall()

            actual_track = [
                {
                    "latitude": float(r.latitude) if r.latitude else None,
                    "longitude": float(r.longitude) if r.longitude else None,
                    "altitude": r.altitude,
                    "speed": r.speed,
                    "heading": r.heading,
                    "timestamp": (
                        r.time_at_position.isoformat() if r.time_at_position else None
                    ),
                }
                for r in track_rows
            ]

            # ── Deviation records ─────────────────────────────────────────────
            deviation_rows = session.execute(
                text(
                    """
                    SELECT actual_latitude, actual_longitude, actual_altitude,
                           actual_speed, timestamp, nearest_fix_name,
                           cross_track_distance_nm, altitude_delta_ft, alert_level
                    FROM flight_deviations
                    WHERE gufi = :gufi
                      AND timestamp >= NOW() - INTERVAL ':hours hours'
                      AND alert_level != 'NORMAL'
                    ORDER BY timestamp ASC
                    """.replace(":hours hours", f"{hours} hours")
                ),
                {"gufi": gufi},
            ).fetchall()

            deviations = [
                {
                    "latitude": r.actual_latitude,
                    "longitude": r.actual_longitude,
                    "altitude": r.actual_altitude,
                    "speed": r.actual_speed,
                    "timestamp": (
                        r.timestamp.isoformat() if r.timestamp else None
                    ),
                    "nearest_fix": r.nearest_fix_name,
                    "cross_track_nm": r.cross_track_distance_nm,
                    "altitude_delta_ft": r.altitude_delta_ft,
                    "alert_level": r.alert_level,
                }
                for r in deviation_rows
            ]

            # ── Adherence summary ─────────────────────────────────────────────
            if actual_track:
                all_dev_rows = session.execute(
                    text(
                        """
                        SELECT alert_level, COUNT(*) as cnt
                        FROM flight_deviations
                        WHERE gufi = :gufi
                        GROUP BY alert_level
                        """
                    ),
                    {"gufi": gufi},
                ).fetchall()
                counts = {r.alert_level: r.cnt for r in all_dev_rows}
                total = sum(counts.values())
                normal = counts.get("NORMAL", 0)
                adherence_pct = round(normal / total * 100, 1) if total else None
            else:
                adherence_pct = None

            session.close()

            return jsonify(
                {
                    "gufi": gufi,
                    "planned_route": planned_route,
                    "actual_track": actual_track,
                    "deviations": deviations,
                    "adherence_pct": adherence_pct,
                    "planned_waypoint_count": len(planned_route),
                    "track_point_count": len(actual_track),
                }
            )

        except Exception as e:
            logger.error(f"Error building route overlay for {gufi}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/v1/flights/events", methods=["GET"])
    def flight_events_poll():
        """
        Polling endpoint for flight events. Returns events newer than `since`.

        Query params:
          since      – ISO-8601 timestamp (required)
          type       – comma-separated event types to filter (default: all)
          origin     – filter by departure airport (ICAO)
          dest       – filter by arrival airport (ICAO)
          aircraft   – filter by aircraft_id/callsign
          limit      – max records to return (default 100, max 500)
        """
        since_str = request.args.get("since")
        if not since_str:
            return jsonify({"error": "since parameter required (ISO-8601)"}), 400

        try:
            from datetime import datetime
            since = datetime.fromisoformat(since_str.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid since timestamp"}), 400

        event_types = request.args.get("type", "")
        origin = request.args.get("origin", "").upper()
        dest = request.args.get("dest", "").upper()
        aircraft = request.args.get("aircraft", "").upper()
        limit = min(int(request.args.get("limit", 100)), 500)

        try:
            session = SessionLocal()

            filters = ["created_at > :since"]
            params = {"since": since, "limit": limit}

            if event_types:
                types_list = [t.strip().upper() for t in event_types.split(",")]
                types_sql = ", ".join(f"'{t}'" for t in types_list)
                filters.append(f"event_type IN ({types_sql})")

            if aircraft:
                filters.append("aircraft_id = :aircraft")
                params["aircraft"] = aircraft

            where = " AND ".join(filters)
            query = text(
                f"""
                SELECT aircraft_id, gufi, event_type, event_timestamp,
                       event_data, source_facility, created_at
                FROM flight_events
                WHERE {where}
                ORDER BY created_at ASC
                LIMIT :limit
                """
            )
            rows = session.execute(query, params).fetchall()

            events = []
            for r in rows:
                ed = r.event_data or {}
                if isinstance(ed, str):
                    import json as _json
                    try:
                        ed = _json.loads(ed)
                    except Exception:
                        ed = {}

                # Apply origin/dest filters on the event_data payload
                if origin and ed.get("departure_airport", "").upper() != origin:
                    continue
                if dest and ed.get("arrival_airport", "").upper() != dest:
                    continue

                events.append(
                    {
                        "aircraft_id": r.aircraft_id,
                        "gufi": r.gufi,
                        "event_type": r.event_type,
                        "event_timestamp": (
                            r.event_timestamp.isoformat() if r.event_timestamp else None
                        ),
                        "event_data": ed,
                        "source_facility": r.source_facility,
                        "created_at": (
                            r.created_at.isoformat() if r.created_at else None
                        ),
                    }
                )

            session.close()
            return jsonify({"events": events, "count": len(events)})

        except Exception as e:
            logger.error(f"Error polling flight events: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/v1/subscriptions", methods=["POST"])
    @limiter.limit("10/minute")
    def create_subscription():
        """
        Register a new notification subscription.

        Body (JSON):
          apprise_url   – required. Apprise URL (slack://, discord://, mailto://, etc.)
          label         – optional human label
          event_types   – optional list of event types (default: all)
          filter_origin – optional ICAO departure filter
          filter_dest   – optional ICAO destination filter
          filter_aircraft – optional aircraft_id filter
          filter_alert_level – optional minimum deviation alert level
        """
        body = request.get_json(silent=True) or {}
        apprise_url = body.get("apprise_url", "").strip()
        if not apprise_url:
            return jsonify({"error": "apprise_url is required"}), 400

        try:
            session = SessionLocal()
            from models.sqlalchemy.flight_overlay import NotificationSubscriptionDBModel

            sub = NotificationSubscriptionDBModel(
                apprise_url=apprise_url,
                label=body.get("label"),
                event_types=body.get("event_types") or [],
                filter_origin=(body.get("filter_origin") or "").upper() or None,
                filter_destination=(body.get("filter_dest") or "").upper() or None,
                filter_aircraft_id=(body.get("filter_aircraft") or "").upper() or None,
                filter_alert_level=(body.get("filter_alert_level") or "").upper() or None,
                is_active=True,
            )
            session.add(sub)
            session.commit()
            sub_id = sub.id
            session.close()

            return jsonify({"id": sub_id, "status": "created"}), 201

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/v1/subscriptions/<int:sub_id>", methods=["DELETE"])
    def delete_subscription(sub_id: int):
        """Deactivate a notification subscription."""
        try:
            session = SessionLocal()
            from models.sqlalchemy.flight_overlay import NotificationSubscriptionDBModel

            sub = (
                session.query(NotificationSubscriptionDBModel)
                .filter_by(id=sub_id)
                .first()
            )
            if not sub:
                session.close()
                return jsonify({"error": "Subscription not found"}), 404

            sub.is_active = False
            session.commit()
            session.close()
            return jsonify({"id": sub_id, "status": "deactivated"})

        except Exception as e:
            logger.error(f"Error deleting subscription {sub_id}: {e}")
            return jsonify({"error": str(e)}), 500

    # ── Flow probability ──────────────────────────────────────────────────────

    @app.route("/v1/airports/<icao>/flow-forecast", methods=["GET"])
    @limiter.limit("30/minute")
    def flow_forecast_single(icao: str):
        """
        Flow control probability for a single airport.

        Query params:
          hours  – forecast window in hours (default 2, max 6)

        Response includes:
          flow_probability  – 0.0 to 1.0
          risk_level        – VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH
          confidence        – HIGH / MEDIUM / LOW  (reflects data availability)
          risk_factors      – ordered list of contributing factors with weights
          current_conditions – METAR summary
          model_version     – "heuristic-v1" until ML model is trained
        """
        hours = min(int(request.args.get("hours", 2)), 6)
        try:
            from services.flow_probability_service import predict_flow_probability
            result = predict_flow_probability(icao.upper(), window_hours=hours)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Flow forecast error for {icao}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/v1/airports/flow-forecast", methods=["GET"])
    @limiter.limit("20/minute")
    def flow_forecast_batch():
        """
        Flow control probability for multiple airports in one call.
        Results sorted by probability descending so highest-risk airports
        appear first — useful for dashboard overviews.

        Query params:
          airports  – comma-separated ICAO codes (e.g. KLAX,KJFK,KORD)
          hours     – forecast window in hours (default 2, max 6)

        Example:
          GET /v1/airports/flow-forecast?airports=KLAX,KJFK,KORD,KATL&hours=2
        """
        airports_str = request.args.get("airports", "")
        if not airports_str:
            return jsonify({"error": "airports parameter required (comma-separated ICAO codes)"}), 400

        airports = [a.strip().upper() for a in airports_str.split(",") if a.strip()]
        if len(airports) > 50:
            return jsonify({"error": "Maximum 50 airports per batch request"}), 400

        hours = min(int(request.args.get("hours", 2)), 6)
        try:
            from services.flow_probability_service import batch_predict
            results = batch_predict(airports, window_hours=hours)
            return jsonify({"airports": results, "count": len(results)})
        except Exception as e:
            logger.error(f"Batch flow forecast error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/v1/airports/<icao>/flow-history", methods=["GET"])
    def flow_forecast_history(icao: str):
        """
        Historical flow probability predictions for trend analysis.
        Returns the last N predictions stored for this airport.

        Query params:
          hours  – how many hours of history to return (default 24)
          limit  – max records (default 50, max 500)
        """
        hours = int(request.args.get("hours", 24))
        limit = min(int(request.args.get("limit", 50)), 500)
        try:
            session = SessionLocal()
            rows = session.execute(
                text(
                    """
                    SELECT predicted_at, window_hours, flow_probability,
                           risk_level, confidence, flight_category,
                           ceiling_ft, visibility_sm, active_tmi_types,
                           taf_trend, risk_factors, actual_flow_control
                    FROM flow_predictions
                    WHERE airport_icao = :icao
                      AND predicted_at >= NOW() - INTERVAL ':hours hours'
                    ORDER BY predicted_at DESC
                    LIMIT :limit
                    """.replace(":hours hours", f"{hours} hours")
                ),
                {"icao": icao.upper(), "limit": limit},
            ).fetchall()

            history = [
                {
                    "predicted_at": r.predicted_at.isoformat() if r.predicted_at else None,
                    "window_hours": r.window_hours,
                    "flow_probability": r.flow_probability,
                    "risk_level": r.risk_level,
                    "confidence": r.confidence,
                    "flight_category": r.flight_category,
                    "ceiling_ft": r.ceiling_ft,
                    "visibility_sm": r.visibility_sm,
                    "active_tmi": r.active_tmi_types,
                    "taf_trend": r.taf_trend,
                    "risk_factors": r.risk_factors,
                    "actual_flow_control": r.actual_flow_control,
                }
                for r in rows
            ]

            session.close()
            return jsonify({"airport": icao.upper(), "history": history, "count": len(history)})

        except Exception as e:
            logger.error(f"Flow history error for {icao}: {e}")
            return jsonify({"error": str(e)}), 500
