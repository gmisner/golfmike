"""
Example Alert System Implementation
Shows how to detect and create alerts based on route assignments and track updates
"""

from sqlalchemy import text
from db_config import SessionLocal
from datetime import datetime
import json


def create_route_assignment_alert(session, gufi: str, route_data: dict, source_facility: str):
    """Create an alert when ATC assigns a new route (from FlightScheduleActivate)"""
    alert_data = {
        "route_data": route_data,
        "source_facility": source_facility,
        "assigned_at": datetime.utcnow().isoformat()
    }
    
    session.execute(
        text("""
            INSERT INTO flight_alerts (gufi, alert_type, severity, message, alert_data)
            VALUES (:gufi, 'ROUTE_ASSIGNED', 'INFO', :message, :alert_data)
        """),
        {
            "gufi": gufi,
            "message": f"New route assigned by {source_facility}",
            "alert_data": json.dumps(alert_data)
        }
    )


def check_route_deviation(session, gufi: str, current_lat: float, current_lon: float, threshold_nm: float = 5.0):
    """Check if aircraft is deviating from assigned route"""
    result = session.execute(
        text("SELECT calculate_route_deviation(:gufi, :lat, :lon) as distance"),
        {
            "gufi": gufi,
            "lat": current_lat,
            "lon": current_lon
        }
    )
    
    distance_km = result.scalar()
    distance_nm = distance_km * 0.539957  # Convert km to nautical miles
    
    if distance_nm > threshold_nm:
        # Determine severity based on deviation distance
        if distance_nm > 20:
            severity = "CRITICAL"
        elif distance_nm > 10:
            severity = "WARNING"
        else:
            severity = "INFO"
        
        alert_data = {
            "deviation_distance_nm": round(distance_nm, 2),
            "current_position": {"lat": current_lat, "lon": current_lon},
            "threshold_nm": threshold_nm
        }
        
        session.execute(
            text("""
                INSERT INTO flight_alerts (gufi, alert_type, severity, message, alert_data)
                VALUES (:gufi, 'ROUTE_DEVIATION', :severity, :message, :alert_data)
            """),
            {
                "gufi": gufi,
                "severity": severity,
                "message": f"Aircraft is {round(distance_nm, 2)}nm off assigned route",
                "alert_data": json.dumps(alert_data)
            }
        )
        return True
    return False


def check_altitude_deviation(session, gufi: str, current_altitude: int, threshold_ft: int = 1000):
    """Check if aircraft altitude deviates from assigned altitude"""
    # Get latest route assignment
    result = session.execute(
        text("""
            SELECT assigned_altitude 
            FROM route_assignments 
            WHERE gufi = :gufi 
            ORDER BY assigned_at DESC 
            LIMIT 1
        """),
        {"gufi": gufi}
    )
    
    assigned_altitude = result.scalar()
    
    if assigned_altitude and current_altitude:
        deviation = abs(current_altitude - assigned_altitude)
        
        if deviation > threshold_ft:
            severity = "WARNING" if deviation > 2000 else "INFO"
            
            alert_data = {
                "current_altitude": current_altitude,
                "assigned_altitude": assigned_altitude,
                "deviation_ft": deviation,
                "threshold_ft": threshold_ft
            }
            
            session.execute(
                text("""
                    INSERT INTO flight_alerts (gufi, alert_type, severity, message, alert_data)
                    VALUES (:gufi, 'ALTITUDE_DEVIATION', :severity, :message, :alert_data)
                """),
                {
                    "gufi": gufi,
                    "severity": severity,
                    "message": f"Aircraft at {current_altitude}ft, assigned {assigned_altitude}ft (deviation: {deviation}ft)",
                    "alert_data": json.dumps(alert_data)
                }
            )
            return True
    return False


def process_track_update(gufi: str, latitude: float, longitude: float, altitude: int, speed: int, time_at_position: datetime):
    """Process a track update and check for deviations"""
    session = SessionLocal()
    try:
        # Store track update
        session.execute(
            text("""
                INSERT INTO track_updates (gufi, latitude, longitude, altitude, speed, time_at_position)
                VALUES (:gufi, :lat, :lon, :alt, :speed, :time_at_pos)
            """),
            {
                "gufi": gufi,
                "lat": latitude,
                "lon": longitude,
                "alt": altitude,
                "speed": speed,
                "time_at_pos": time_at_position
            }
        )
        
        # Check for deviations
        check_route_deviation(session, gufi, latitude, longitude)
        check_altitude_deviation(session, gufi, altitude)
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def process_route_assignment(gufi: str, aircraft_id: str, route_data: dict, assigned_altitude: int, 
                            assigned_speed: int, etd: datetime, eta: datetime, source_facility: str):
    """Process a route assignment from FlightScheduleActivate message"""
    session = SessionLocal()
    try:
        # Ensure flight exists
        session.execute(
            text("""
                INSERT INTO flights (gufi, aircraft_id, current_status, updated_at)
                VALUES (:gufi, :aircraft_id, 'ACTIVE', NOW())
                ON CONFLICT (gufi) 
                DO UPDATE SET current_status = 'ACTIVE', updated_at = NOW()
            """),
            {"gufi": gufi, "aircraft_id": aircraft_id}
        )
        
        # Store route assignment
        session.execute(
            text("""
                INSERT INTO route_assignments (gufi, assigned_altitude, assigned_speed, route_data, etd, eta, source_facility)
                VALUES (:gufi, :alt, :speed, :route_data, :etd, :eta, :facility)
            """),
            {
                "gufi": gufi,
                "alt": assigned_altitude,
                "speed": assigned_speed,
                "route_data": json.dumps(route_data),
                "etd": etd,
                "eta": eta,
                "facility": source_facility
            }
        )
        
        # Create alert for new route assignment
        create_route_assignment_alert(session, gufi, route_data, source_facility)
        
        # Extract and store waypoints
        route_assignment_id = session.execute(
            text("SELECT id FROM route_assignments WHERE gufi = :gufi ORDER BY assigned_at DESC LIMIT 1"),
            {"gufi": gufi}
        ).scalar()
        
        if route_assignment_id and "waypoints" in route_data:
            for waypoint in route_data["waypoints"]:
                session.execute(
                    text("""
                        INSERT INTO route_waypoints 
                        (route_assignment_id, sequence_number, waypoint_type, name, latitude, longitude, elapsed_time, altitude)
                        VALUES (:route_id, :seq, :type, :name, :lat, :lon, :elapsed, :alt)
                    """),
                    {
                        "route_id": route_assignment_id,
                        "seq": waypoint.get("sequenceNumber"),
                        "type": waypoint.get("type", "WAYPOINT"),
                        "name": waypoint.get("name"),
                        "lat": waypoint.get("latitudeDecimal"),
                        "lon": waypoint.get("longitudeDecimal"),
                        "elapsed": waypoint.get("elapsedTime"),
                        "alt": waypoint.get("altitude")
                    }
                )
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def get_flight_alerts(gufi: str, unacknowledged_only: bool = True):
    """Get alerts for a specific flight"""
    session = SessionLocal()
    try:
        query = """
            SELECT id, alert_type, severity, message, alert_data, created_at, acknowledged
            FROM flight_alerts
            WHERE gufi = :gufi
        """
        params = {"gufi": gufi}
        
        if unacknowledged_only:
            query += " AND acknowledged = FALSE"
        
        query += " ORDER BY created_at DESC"
        
        result = session.execute(text(query), params)
        return result.fetchall()
    finally:
        session.close()


# Example usage:
if __name__ == "__main__":
    # Example: Process a route assignment
    route_data = {
        "waypoints": [
            {"sequenceNumber": 1, "latitudeDecimal": 40.69, "longitudeDecimal": -74.17, "elapsedTime": 0},
            {"sequenceNumber": 2, "latitudeDecimal": 40.74, "longitudeDecimal": -74.10, "elapsedTime": 81},
        ],
        "fixes": [
            {"sequenceNumber": 1, "name": "EWR"},
            {"sequenceNumber": 2, "name": "MERIT", "elapsedTime": 704}
        ]
    }
    
    process_route_assignment(
        gufi="KL45173200",
        aircraft_id="N78HV",
        route_data=route_data,
        assigned_altitude=310,
        assigned_speed=453,
        etd=datetime.utcnow(),
        eta=datetime.utcnow(),
        source_facility="TFMS"
    )
    
    # Example: Process a track update and check for deviations
    process_track_update(
        gufi="KL45173200",
        latitude=40.69,
        longitude=-74.17,
        altitude=310,
        speed=450,
        time_at_position=datetime.utcnow()
    )
    
    # Get alerts
    alerts = get_flight_alerts("KL45173200", unacknowledged_only=True)
    for alert in alerts:
        print(f"Alert: {alert.alert_type} - {alert.message}")

