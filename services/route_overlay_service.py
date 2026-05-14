"""
Route overlay service: compares actual track points against the planned route
and writes FlightDeviationDBModel records. Called from the track_information
storer each time a new position update is received for a tracked flight.

Cross-track distance (XTD) uses the haversine formula on the great-circle
path between consecutive planned waypoints. This is accurate to within ~0.3%
for typical en-route distances.

Alert thresholds:
  NORMAL:  XTD < 2 nm  AND  altitude delta < 500 ft
  CAUTION: XTD ≥ 2 nm  OR   altitude delta ≥ 500 ft
  WARNING: XTD ≥ 5 nm  OR   altitude delta ≥ 1000 ft
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session

from models.sqlalchemy.flight_overlay import PlannedWaypointDBModel, FlightDeviationDBModel
from services.notification_service import send_flight_event
from utils.logger import main_logger as logger


# ── Haversine geometry ────────────────────────────────────────────────────────

_R_NM = 3440.065  # Earth radius in nautical miles


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _R_NM * math.asin(math.sqrt(a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, in radians."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return math.atan2(x, y)


def _cross_track_distance_nm(
    lat_p: float, lon_p: float,   # actual position
    lat_a: float, lon_a: float,   # segment start
    lat_b: float, lon_b: float,   # segment end
) -> float:
    """
    Signed cross-track distance from point P to the great-circle path A→B.
    Positive = right of track, negative = left of track.
    """
    d_ap = _haversine_nm(lat_a, lon_a, lat_p, lon_p) / _R_NM  # angular distance
    theta_ap = _bearing(lat_a, lon_a, lat_p, lon_p)
    theta_ab = _bearing(lat_a, lon_a, lat_b, lon_b)
    return math.asin(math.sin(d_ap) * math.sin(theta_ap - theta_ab)) * _R_NM


def _along_track_fraction(
    lat_p: float, lon_p: float,
    lat_a: float, lon_a: float,
    lat_b: float, lon_b: float,
) -> float:
    """
    Returns how far along segment A→B the closest point to P lies (0.0–1.0).
    Values outside [0, 1] mean P is before A or after B.
    """
    d_ab = _haversine_nm(lat_a, lon_a, lat_b, lon_b)
    if d_ab < 0.01:  # segment is essentially a point
        return 0.0
    d_ap = _haversine_nm(lat_a, lon_a, lat_p, lon_p)
    xtd = abs(_cross_track_distance_nm(lat_p, lon_p, lat_a, lon_a, lat_b, lon_b))
    # along-track distance via Pythagorean approximation on the sphere
    atd_nm = math.sqrt(max(d_ap ** 2 - xtd ** 2, 0.0))
    return atd_nm / d_ab


# ── Alert level ───────────────────────────────────────────────────────────────

def _alert_level(xtd_nm: float, alt_delta_ft: int) -> str:
    xtd = abs(xtd_nm)
    alt = abs(alt_delta_ft)
    if xtd >= 5.0 or alt >= 1000:
        return "WARNING"
    if xtd >= 2.0 or alt >= 500:
        return "CAUTION"
    return "NORMAL"


# ── Planned waypoint fetch ────────────────────────────────────────────────────

def _get_planned_waypoints(gufi: str, session: Session) -> List[PlannedWaypointDBModel]:
    return (
        session.query(PlannedWaypointDBModel)
        .filter(
            PlannedWaypointDBModel.gufi == gufi,
            PlannedWaypointDBModel.latitude.isnot(None),
            PlannedWaypointDBModel.longitude.isnot(None),
        )
        .order_by(PlannedWaypointDBModel.sequence)
        .all()
    )


# ── Nearest segment finder ────────────────────────────────────────────────────

def _find_nearest_segment(
    lat: float,
    lon: float,
    waypoints: List[PlannedWaypointDBModel],
) -> Tuple[Optional[int], Optional[str], float]:
    """
    Find the planned route segment closest to the actual position.

    Returns:
        (segment_start_sequence, nearest_fix_name, cross_track_distance_nm)
    """
    best_xtd = float("inf")
    best_seq = None
    best_fix = None

    for i in range(len(waypoints) - 1):
        a = waypoints[i]
        b = waypoints[i + 1]
        try:
            frac = _along_track_fraction(lat, lon, a.latitude, a.longitude, b.latitude, b.longitude)
            # Only consider segments where the projection falls within the segment
            if frac < -0.1 or frac > 1.1:
                continue
            xtd = _cross_track_distance_nm(lat, lon, a.latitude, a.longitude, b.latitude, b.longitude)
            if abs(xtd) < abs(best_xtd):
                best_xtd = xtd
                best_seq = a.sequence
                best_fix = b.fix_name
        except Exception:
            continue

    # If no segment matched (aircraft before departure or past destination), use nearest point
    if best_seq is None and waypoints:
        min_dist = float("inf")
        for w in waypoints:
            d = _haversine_nm(lat, lon, w.latitude, w.longitude)
            if d < min_dist:
                min_dist = d
                best_xtd = min_dist
                best_seq = w.sequence
                best_fix = w.fix_name

    return best_seq, best_fix, best_xtd


# ── Public entry point ────────────────────────────────────────────────────────

def process_track_point(
    gufi: str,
    aircraft_id: str,
    latitude: float,
    longitude: float,
    altitude: Optional[int],
    speed: Optional[int],
    timestamp: datetime,
    filed_altitude: Optional[int],
    event_data: Dict[str, Any],
    session: Session,
) -> Optional[FlightDeviationDBModel]:
    """
    Compare one track point against the planned route and persist a deviation
    record. Triggers a notification if alert level is CAUTION or WARNING.

    Args:
        gufi:           Globally unique flight identifier
        aircraft_id:    Aircraft callsign/tail number
        latitude:       Actual latitude (decimal degrees)
        longitude:      Actual longitude (decimal degrees)
        altitude:       Actual altitude in feet (None if unavailable)
        speed:          Actual ground speed in knots
        timestamp:      Position timestamp (timezone-aware)
        filed_altitude: Filed cruise altitude in feet (from flight plan)
        event_data:     Dict with departure/arrival airports for notification body
        session:        Active SQLAlchemy session

    Returns:
        The persisted FlightDeviationDBModel, or None if planned route unavailable
    """
    planned = _get_planned_waypoints(gufi, session)
    if len(planned) < 2:
        return None  # No decoded route yet — skip silently

    nearest_seq, nearest_fix, xtd_nm = _find_nearest_segment(latitude, longitude, planned)

    alt_delta = 0
    if altitude is not None and filed_altitude is not None:
        alt_delta = altitude - filed_altitude

    level = _alert_level(xtd_nm, alt_delta)

    deviation = FlightDeviationDBModel(
        gufi=gufi,
        aircraft_id=aircraft_id,
        actual_latitude=latitude,
        actual_longitude=longitude,
        actual_altitude=altitude,
        actual_speed=speed,
        timestamp=timestamp,
        nearest_planned_sequence=nearest_seq,
        nearest_fix_name=nearest_fix,
        cross_track_distance_nm=round(xtd_nm, 3),
        altitude_delta_ft=alt_delta,
        alert_level=level,
        notification_sent=False,
    )
    session.add(deviation)

    if level in ("CAUTION", "WARNING"):
        notif_data = {
            **event_data,
            "gufi": gufi,
            "aircraft_id": aircraft_id,
            "cross_track_nm": xtd_nm,
            "altitude_delta_ft": alt_delta,
            "alert_level": level,
            "nearest_fix": nearest_fix or "",
        }
        send_flight_event("DEVIATION", notif_data, session)
        deviation.notification_sent = True

    try:
        session.commit()
        if level != "NORMAL":
            logger.warning(
                f"[{level}] {aircraft_id} ({gufi}): XTD={xtd_nm:.1f}nm "
                f"ALT_Δ={alt_delta:+d}ft near {nearest_fix}"
            )
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to store deviation for {gufi}: {e}")
        return None

    return deviation


def store_planned_waypoints(
    gufi: str,
    aircraft_id: str,
    waypoints: List[Dict],
    session: Session,
    route_source: str = "FILED",
) -> int:
    """
    Persist decoded planned waypoints. Replaces any existing waypoints for
    this GUFI+source combination (handles amendments).

    Args:
        gufi:         Flight GUFI
        aircraft_id:  Aircraft ID
        waypoints:    Output of route_decoder.decode_route()
        session:      Active SQLAlchemy session
        route_source: "FILED" or "AMENDED"

    Returns:
        Number of waypoints stored
    """
    try:
        # Delete existing planned waypoints for this GUFI and source
        session.query(PlannedWaypointDBModel).filter(
            PlannedWaypointDBModel.gufi == gufi,
            PlannedWaypointDBModel.route_source == route_source,
        ).delete(synchronize_session=False)

        records = [
            PlannedWaypointDBModel(
                gufi=gufi,
                aircraft_id=aircraft_id,
                sequence=w["sequence"],
                fix_name=w["fix_name"],
                latitude=w.get("latitude"),
                longitude=w.get("longitude"),
                altitude_restriction=w.get("altitude_restriction"),
                speed_restriction=w.get("speed_restriction"),
                route_source=route_source,
            )
            for w in waypoints
        ]
        session.add_all(records)
        session.commit()
        logger.info(
            f"Stored {len(records)} planned waypoints for {aircraft_id} ({gufi}) [{route_source}]"
        )
        return len(records)

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to store planned waypoints for {gufi}: {e}")
        return 0
