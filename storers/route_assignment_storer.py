"""
Route Assignment Storer
Stores route assignment data from FlightScheduleActivate messages
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError
from db_config import SessionLocal
from datetime import datetime
import json


def store_route_assignment(
    route_data: Dict[str, Any],
    session: Session = None,
):
    """
    Store route assignment data from FlightScheduleActivate message
    
    Args:
        route_data: Dictionary containing parsed route assignment data
        session: SQLAlchemy session (optional, will create if not provided)
    """
    created_locally = False
    if session is None:
        logger.debug("No session provided, creating a new session")
        session = SessionLocal()
        created_locally = True
    elif not isinstance(session, Session):
        logger.error(
            f"Invalid session type: {type(session)}. Expected <class 'sqlalchemy.orm.session.Session'>."
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")
    
    try:
        gufi = route_data.get("gufi")
        aircraft_id = normalize_aircraft_id(route_data.get("aircraft_id"))
        if aircraft_id:
            route_data["aircraft_id"] = aircraft_id
        
        # If no GUFI, try to find one from existing flight_plan table using aircraft_id
        # This is the proper relationship: aircraft_id → flight_plan → GUFI
        if not gufi:
            flight_ref = route_data.get("flight_reference")
            if aircraft_id:
                # Primary strategy: Look up GUFI from flight_plan by aircraft_id
                # This is the correct relationship - flight plans are tied to aircraft_id
                result = session.execute(
                    text("""
                        SELECT gufi, flight_reference, igtd 
                        FROM flight_plan 
                        WHERE aircraft_id = :aircraft_id 
                        AND gufi IS NOT NULL
                        ORDER BY id DESC
                        LIMIT 1
                    """),
                    {"aircraft_id": aircraft_id}
                )
                row = result.fetchone()
                if row and row[0]:
                    gufi = row[0]
                    logger.info(f"✅ Found GUFI {gufi} from flight_plan for aircraft {aircraft_id}")
                    # Optionally match by flight_reference if available
                    if flight_ref and row[1] and flight_ref != row[1]:
                        logger.debug(f"Flight reference mismatch: route has {flight_ref}, flight_plan has {row[1]}")
                elif flight_ref:
                    # Fallback: Try by flight reference
                    result = session.execute(
                        text("""
                            SELECT gufi FROM flight_plan 
                            WHERE flight_reference = :flight_ref
                            AND gufi IS NOT NULL
                            ORDER BY id DESC
                            LIMIT 1
                        """),
                        {"flight_ref": flight_ref}
                    )
                    existing_gufi = result.scalar()
                    if existing_gufi:
                        gufi = existing_gufi
                        logger.info(f"Found GUFI {gufi} by flight_reference {flight_ref}")
        
        # If still no GUFI, create a placeholder GUFI based on aircraft_id and timestamp
        # This allows us to store the route assignment even without a proper GUFI
        if not gufi:
            if aircraft_id:
                # Create a temporary GUFI - in production you might want to handle this differently
                import hashlib
                flight_ref = route_data.get("flight_reference", "")
                timestamp = route_data.get("source_timestamp", datetime.utcnow().isoformat())
                gufi_input = f"{aircraft_id}_{flight_ref}_{timestamp}"
                gufi = f"TEMP_{hashlib.md5(gufi_input.encode()).hexdigest()[:12].upper()}"
                logger.warning(f"Created temporary GUFI {gufi} for aircraft {aircraft_id}")
            else:
                logger.warning(f"No GUFI and no aircraft_id found in route assignment data, skipping")
                return
        
        if not aircraft_id:
            logger.warning("No aircraft_id found in route assignment data, skipping")
            return
        
        # Ensure aircraft exists in aircraft table (required for foreign key constraints)
        # This must happen before creating flights records due to foreign key constraints
        session.execute(
            text("""
                INSERT INTO aircraft (aircraft_id)
                VALUES (:aircraft_id)
                ON CONFLICT (aircraft_id) DO NOTHING
            """),
            {"aircraft_id": aircraft_id}
        )
        logger.debug(f"Ensured aircraft {aircraft_id} exists in aircraft table")
        
        # Parse datetime strings
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            try:
                # Try ISO format
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                try:
                    # Try other formats
                    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"]:
                        return datetime.strptime(dt_str, fmt)
                except:
                    logger.warning(f"Could not parse datetime: {dt_str}")
                    return None
        
        etd = parse_datetime(route_data.get("etd"))
        eta = parse_datetime(route_data.get("eta"))
        source_timestamp = parse_datetime(route_data.get("source_timestamp"))
        
        # Ensure flight exists in flights table
        # If GUFI is a temporary one, we might want to update it later when we find the real GUFI
        session.execute(
            text("""
                INSERT INTO flights (gufi, aircraft_id, flight_reference, departure_airport, arrival_airport, 
                                     scheduled_departure, scheduled_arrival, current_status, updated_at)
                VALUES (:gufi, :aircraft_id, :flight_ref, :dep_apt, :arr_apt, :dep_time, :arr_time, :status, NOW())
                ON CONFLICT (gufi) 
                DO UPDATE SET 
                    aircraft_id = EXCLUDED.aircraft_id,
                    flight_reference = EXCLUDED.flight_reference,
                    departure_airport = EXCLUDED.departure_airport,
                    arrival_airport = EXCLUDED.arrival_airport,
                    scheduled_departure = EXCLUDED.scheduled_departure,
                    scheduled_arrival = EXCLUDED.scheduled_arrival,
                    current_status = EXCLUDED.current_status,
                    updated_at = NOW()
            """),
            {
                "gufi": gufi,
                "aircraft_id": aircraft_id,
                "flight_ref": route_data.get("flight_reference"),
                "dep_apt": route_data.get("departure_airport"),
                "arr_apt": route_data.get("arrival_airport"),
                "dep_time": parse_datetime(route_data.get("igtd")),
                "arr_time": eta,
                "status": route_data.get("flight_status", "ACTIVE")
            }
        )
        
        # Try to find a real GUFI from flight_plan table using aircraft_id
        # This is the proper relationship: aircraft_id → flight_plan → GUFI
        if gufi and gufi.startswith("TEMP_"):
            temp_gufi = gufi  # Save the temp GUFI before reassigning
            # Look for a real GUFI from flight_plan
            result = session.execute(
                text("""
                    SELECT gufi FROM flight_plan 
                    WHERE aircraft_id = :aircraft_id 
                    AND gufi IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"aircraft_id": aircraft_id}
            )
            real_gufi = result.scalar()
            
            if real_gufi:
                logger.info(f"Found real GUFI {real_gufi} for aircraft {aircraft_id}, updating flight record")
                # Update the flight record with the real GUFI
                session.execute(
                    text("""
                        UPDATE flights 
                        SET gufi = :real_gufi, updated_at = NOW()
                        WHERE gufi = :temp_gufi
                    """),
                    {"real_gufi": real_gufi, "temp_gufi": temp_gufi}
                )
                gufi = real_gufi  # Use the real GUFI for the route assignment
        
        # Store route assignment
        route_data_json = json.dumps(route_data.get("route_data", {}))
        
        result = session.execute(
            text("""
                INSERT INTO route_assignments 
                (gufi, assigned_altitude, assigned_speed, route_data, etd, eta, source_facility, assigned_at)
                VALUES (:gufi, :alt, :speed, :route_data, :etd, :eta, :facility, COALESCE(:source_ts, NOW()))
                RETURNING id
            """),
            {
                "gufi": gufi,
                "alt": route_data.get("assigned_altitude"),
                "speed": route_data.get("assigned_speed"),
                "route_data": route_data_json,
                "etd": etd,
                "eta": eta,
                "facility": route_data.get("source_facility"),
                "source_ts": source_timestamp
            }
        )
        
        route_assignment_id = result.scalar()
        
        # Store waypoints
        waypoints = route_data.get("route_data", {}).get("waypoints", [])
        for waypoint in waypoints:
            try:
                session.execute(
                    text("""
                        INSERT INTO route_waypoints 
                        (route_assignment_id, sequence_number, waypoint_type, latitude, longitude, elapsed_time)
                        VALUES (:route_id, :seq, 'WAYPOINT', :lat, :lon, :elapsed)
                    """),
                    {
                        "route_id": route_assignment_id,
                        "seq": int(waypoint.get("sequence_number", 0)) if waypoint.get("sequence_number") else None,
                        "lat": float(waypoint.get("latitude")) if waypoint.get("latitude") else None,
                        "lon": float(waypoint.get("longitude")) if waypoint.get("longitude") else None,
                        "elapsed": int(waypoint.get("elapsed_time")) if waypoint.get("elapsed_time") else None
                    }
                )
            except Exception as e:
                logger.warning(f"Error storing waypoint: {e}")
        
        # Store fixes as waypoints too
        fixes = route_data.get("route_data", {}).get("fixes", [])
        for fix in fixes:
            try:
                session.execute(
                    text("""
                        INSERT INTO route_waypoints 
                        (route_assignment_id, sequence_number, waypoint_type, name, elapsed_time)
                        VALUES (:route_id, :seq, 'FIX', :name, :elapsed)
                    """),
                    {
                        "route_id": route_assignment_id,
                        "seq": int(fix.get("sequence_number", 0)) if fix.get("sequence_number") else None,
                        "name": fix.get("name"),
                        "elapsed": int(fix.get("elapsed_time")) if fix.get("elapsed_time") else None
                    }
                )
            except Exception as e:
                logger.warning(f"Error storing fix: {e}")
        
        # Create alert for new route assignment
        session.execute(
            text("""
                INSERT INTO flight_alerts (gufi, alert_type, severity, message, alert_data)
                VALUES (:gufi, 'ROUTE_ASSIGNED', 'INFO', :message, :alert_data)
            """),
            {
                "gufi": gufi,
                "message": f"New route assigned by {route_data.get('source_facility', 'ATC')}",
                "alert_data": json.dumps({
                    "source_facility": route_data.get("source_facility"),
                    "assigned_altitude": route_data.get("assigned_altitude"),
                    "assigned_speed": route_data.get("assigned_speed"),
                    "assigned_at": datetime.utcnow().isoformat()
                })
            }
        )
        
        session.commit()
        logger.info(f"Successfully stored route assignment for GUFI: {gufi}, Aircraft: {aircraft_id}")
        
    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError storing route assignment: {}", str(e), exc_info=True)
        session.rollback()
        raise
    except Exception as e:
        logger.error("Error storing route assignment: {}", str(e), exc_info=True)
        session.rollback()
        raise
    finally:
        if created_locally:
            session.close()
            logger.debug("Session closed.")


def store_route_assignments(
    route_data_list: List[Dict[str, Any]],
    session: Session = None,
):
    """
    Store multiple route assignments
    
    Args:
        route_data_list: List of dictionaries containing parsed route assignment data
        session: SQLAlchemy session (optional, will create if not provided)
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    
    try:
        for route_data in route_data_list:
            store_route_assignment(route_data, session=session)
        
        logger.success(f"Successfully stored {len(route_data_list)} route assignments")
    except Exception as e:
        logger.error("Error storing route assignments: {}", str(e), exc_info=True)
        raise
    finally:
        if created_locally:
            session.close()

