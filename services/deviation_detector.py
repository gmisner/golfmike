"""
Route Deviation Detection Service
Compares actual track positions to assigned route waypoints
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in nautical miles
    
    Args:
        lat1, lon1: Latitude and longitude of first point (in decimal degrees)
        lat2, lon2: Latitude and longitude of second point (in decimal degrees)
    
    Returns:
        Distance in nautical miles
    """
    # Earth's radius in nautical miles
    R = 3440.065  # nautical miles
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def find_nearest_waypoint(
    lat: float, 
    lon: float, 
    waypoints: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find the nearest waypoint to the given position
    
    Args:
        lat, lon: Current position
        waypoints: List of waypoint dictionaries with 'latitude' and 'longitude' keys
    
    Returns:
        Dictionary with 'waypoint' (the nearest waypoint) and 'distance' (distance in NM)
    """
    if not waypoints:
        return None
    
    min_distance = float('inf')
    nearest = None
    
    for waypoint in waypoints:
        try:
            wp_lat = float(waypoint.get('latitude', 0))
            wp_lon = float(waypoint.get('longitude', 0))
            
            if wp_lat == 0 and wp_lon == 0:
                continue
            
            distance = haversine_distance(lat, lon, wp_lat, wp_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest = waypoint
        except (ValueError, TypeError):
            continue
    
    if nearest:
        return {
            'waypoint': nearest,
            'distance': min_distance
        }
    
    return None


def calculate_route_deviation(
    gufi: str,
    session: Session = None,
    deviation_threshold_nm: float = 5.0,
    altitude_threshold_ft: int = 1000,
    speed_threshold_kts: int = 50
) -> List[Dict[str, Any]]:
    """
    Calculate deviations from assigned route for a given flight
    
    Args:
        gufi: Globally unique flight identifier
        session: Database session
        deviation_threshold_nm: Distance threshold in nautical miles (default 5 NM)
        altitude_threshold_ft: Altitude deviation threshold in feet (default 1000 ft)
        speed_threshold_kts: Speed deviation threshold in knots (default 50 kts)
    
    Returns:
        List of deviation alerts
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    
    alerts = []
    
    try:
        # Get the most recent track update for this flight
        result = session.execute(
            text("""
                SELECT 
                    tu.aircraft_id,
                    tu.gufi,
                    tu.latitude,
                    tu.longitude,
                    tu.altitude,
                    tu.speed,
                    tu.time_at_position,
                    ra.assigned_altitude,
                    ra.assigned_speed,
                    ra.route_data
                FROM track_updates tu
                INNER JOIN flights f ON tu.gufi = f.gufi
                LEFT JOIN route_assignments ra ON tu.gufi = ra.gufi
                WHERE tu.gufi = :gufi
                ORDER BY tu.time_at_position DESC
                LIMIT 1
            """),
            {"gufi": gufi}
        )
        
        row = result.fetchone()
        if not row:
            logger.debug(f"No track update found for GUFI {gufi}")
            return alerts
        
        # Unpack row data
        aircraft_id = row[0]
        current_lat = float(row[2]) if row[2] else None
        current_lon = float(row[3]) if row[3] else None
        current_alt = row[4]
        current_speed = row[5]
        time_at_pos = row[6]
        assigned_alt = row[7]
        assigned_speed = row[8]
        route_data_json = row[9]
        
        if not current_lat or not current_lon:
            logger.debug(f"Invalid position data for GUFI {gufi}")
            return alerts
        
        # Parse route data to get waypoints
        import json
        route_data = {}
        waypoints = []
        
        if route_data_json:
            try:
                if isinstance(route_data_json, str):
                    route_data = json.loads(route_data_json)
                else:
                    route_data = route_data_json
                
                waypoints = route_data.get('waypoints', [])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Could not parse route_data for GUFI {gufi}")
        
        # Check route deviation (distance from assigned waypoints)
        if waypoints:
            nearest = find_nearest_waypoint(current_lat, current_lon, waypoints)
            
            if nearest and nearest['distance'] > deviation_threshold_nm:
                alerts.append({
                    'gufi': gufi,
                    'aircraft_id': aircraft_id,
                    'alert_type': 'ROUTE_DEVIATION',
                    'severity': 'WARNING' if nearest['distance'] < 20 else 'CRITICAL',
                    'message': f"Aircraft {aircraft_id} is {nearest['distance']:.1f} NM off assigned route",
                    'alert_data': {
                        'deviation_distance_nm': round(nearest['distance'], 2),
                        'current_position': {'lat': current_lat, 'lon': current_lon},
                        'nearest_waypoint': nearest['waypoint'],
                        'threshold_nm': deviation_threshold_nm
                    }
                })
        
        # Check altitude deviation
        if assigned_alt and current_alt:
            alt_diff = abs(current_alt - assigned_alt)
            if alt_diff > altitude_threshold_ft:
                alerts.append({
                    'gufi': gufi,
                    'aircraft_id': aircraft_id,
                    'alert_type': 'ALTITUDE_DEVIATION',
                    'severity': 'WARNING' if alt_diff < 2000 else 'CRITICAL',
                    'message': f"Aircraft {aircraft_id} altitude deviation: {alt_diff} ft (assigned: {assigned_alt} ft, current: {current_alt} ft)",
                    'alert_data': {
                        'assigned_altitude_ft': assigned_alt,
                        'current_altitude_ft': current_alt,
                        'deviation_ft': alt_diff,
                        'threshold_ft': altitude_threshold_ft
                    }
                })
        
        # Check speed deviation
        if assigned_speed and current_speed:
            speed_diff = abs(current_speed - assigned_speed)
            if speed_diff > speed_threshold_kts:
                alerts.append({
                    'gufi': gufi,
                    'aircraft_id': aircraft_id,
                    'alert_type': 'SPEED_DEVIATION',
                    'severity': 'INFO',
                    'message': f"Aircraft {aircraft_id} speed deviation: {speed_diff} kts (assigned: {assigned_speed} kts, current: {current_speed} kts)",
                    'alert_data': {
                        'assigned_speed_kts': assigned_speed,
                        'current_speed_kts': current_speed,
                        'deviation_kts': speed_diff,
                        'threshold_kts': speed_threshold_kts
                    }
                })
        
        # Store alerts in database
        for alert in alerts:
            session.execute(
                text("""
                    INSERT INTO flight_alerts 
                    (gufi, alert_type, severity, message, alert_data, created_at)
                    VALUES (:gufi, :alert_type, :severity, :message, :alert_data::jsonb, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "gufi": alert['gufi'],
                    "alert_type": alert['alert_type'],
                    "severity": alert['severity'],
                    "message": alert['message'],
                    "alert_data": json.dumps(alert['alert_data'])
                }
            )
        
        if alerts:
            session.commit()
            logger.info(f"Generated {len(alerts)} deviation alerts for GUFI {gufi}")
        
        return alerts
        
    except Exception as e:
        logger.error("Error calculating route deviation: {}", str(e), exc_info=True)
        if created_locally:
            session.rollback()
        raise
    finally:
        if created_locally:
            session.close()


def check_all_active_flights(
    session: Session = None,
    time_window_minutes: int = 15
) -> Dict[str, Any]:
    """
    Check all active flights for deviations
    
    Args:
        session: Database session
        time_window_minutes: Only check flights with track updates within this window
    
    Returns:
        Dictionary with summary of checks
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    
    try:
        # Get all flights with recent track updates
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        result = session.execute(
            text("""
                SELECT DISTINCT tu.gufi
                FROM track_updates tu
                INNER JOIN route_assignments ra ON tu.gufi = ra.gufi
                WHERE tu.time_at_position >= :cutoff_time
            """),
            {"cutoff_time": cutoff_time}
        )
        
        gufis = [row[0] for row in result.fetchall()]
        
        total_alerts = 0
        for gufi in gufis:
            alerts = calculate_route_deviation(gufi, session=session)
            total_alerts += len(alerts)
        
        return {
            'flights_checked': len(gufis),
            'total_alerts_generated': total_alerts,
            'check_time': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error checking all active flights: {}", str(e), exc_info=True)
        raise
    finally:
        if created_locally:
            session.close()

