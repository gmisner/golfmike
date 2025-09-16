"""
Simple API endpoints for the frontend - works with existing database structure
"""

from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from utils.logger import main_logger as logger
import json

# Database connection
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_simple_api(app: Flask) -> None:
    """Add simple flight tracking endpoints to the Flask app"""

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
                            "description": "Aircraft airborne",
                            "badge_class": "bg-success",
                            "type": "operational",
                        }
                    )
                if oooi_row.on_time:
                    timeline.append(
                        {
                            "time": oooi_row.on_time.isoformat(),
                            "title": "ON — Landing",
                            "description": "Aircraft landed",
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
                for i, point in enumerate(track_rows):
                    if prev_point and point.time_at_position:
                        # Check for significant altitude changes (>5000 ft)
                        if (
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
            return jsonify({"error": "Internal server error"}), 500
