"""
GET /v1/flights/active        — live flights with latest position
GET /v1/flights/search?q=     — typeahead / full search
GET /v1/flights/<ident>       — full detail (position + track + tbfm)
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_flights", __name__, url_prefix="/v1/flights")


def _session():
    return SessionLocal()


def _safe_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ── Active flights ────────────────────────────────────────────────────
@bp.get("/active")
def active_flights():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        with _session() as db:
            rows = db.execute(
                text("""
                    WITH recent_tracks AS (
                        -- aircraft with a position update in the last 2 hours
                        SELECT DISTINCT aircraft_id
                        FROM track_information
                        WHERE time_at_position > TO_CHAR(NOW() - INTERVAL '2 hours',
                                                         'YYYY-MM-DD"T"HH24:MI:SS"Z"')
                    ),
                    active AS (
                        SELECT f.aircraft_id, f.departure_airport, f.arrival_airport,
                               f.scheduled_departure, f.scheduled_arrival, f.current_status, f.gufi
                        FROM flights f
                        INNER JOIN recent_tracks rt ON rt.aircraft_id = f.aircraft_id
                        WHERE f.current_status IN ('ACTIVE', 'IN_FLIGHT')
                        ORDER BY f.scheduled_departure DESC
                        LIMIT :limit
                    ),
                    latest_pos AS (
                        SELECT DISTINCT ON (ti.aircraft_id)
                               ti.aircraft_id, ti.latitude, ti.longitude, ti.altitude, ti.speed
                        FROM track_information ti
                        INNER JOIN active a ON a.aircraft_id = ti.aircraft_id
                        ORDER BY ti.aircraft_id, ti.id DESC
                    )
                    SELECT
                        a.aircraft_id                        AS ident,
                        a.departure_airport                  AS origin,
                        a.arrival_airport                    AS destination,
                        fp."typeOfAircraft_03c"              AS aircraft_type,
                        a.scheduled_departure                AS departure_time,
                        a.scheduled_arrival                  AS arrival_time,
                        COALESCE(a.current_status, 'active') AS status,
                        lp.latitude,
                        lp.longitude,
                        lp.altitude,
                        lp.speed                             AS ground_speed
                    FROM active a
                    LEFT JOIN flight_plan fp ON fp.gufi = a.gufi
                    LEFT JOIN latest_pos lp ON lp.aircraft_id = a.aircraft_id
                    ORDER BY a.scheduled_departure DESC
                """),
                {"limit": limit},
            ).fetchall()

        flights = [
            {
                "ident":         r.ident,
                "origin":        r.origin,
                "destination":   r.destination,
                "aircraft_type": r.aircraft_type,
                "departure_time": r.departure_time.isoformat() if r.departure_time else None,
                "arrival_time":  r.arrival_time.isoformat() if r.arrival_time else None,
                "status":        r.status or "active",
                "latitude":      _safe_float(r.latitude),
                "longitude":     _safe_float(r.longitude),
                "altitude":      _safe_int(r.altitude),
                "ground_speed":  _safe_int(r.ground_speed),
            }
            for r in rows
        ]
        return jsonify({"flights": flights, "total": len(flights)})
    except Exception as e:
        logger.exception("active_flights error")
        return jsonify({"error": str(e)}), 500


# ── Search ────────────────────────────────────────────────────────────
@bp.get("/search")
def search_flights():
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 50)
    if len(q) < 2:
        return jsonify({"flights": [], "total": 0})
    try:
        with _session() as db:
            rows = db.execute(
                text("""
                    SELECT DISTINCT ON (f.aircraft_id)
                        f.aircraft_id                           AS ident,
                        f.departure_airport                     AS origin,
                        f.arrival_airport                       AS destination,
                        fp."typeOfAircraft_03c"                 AS aircraft_type,
                        f.scheduled_departure                   AS departure_time,
                        COALESCE(f.current_status, 'scheduled') AS status
                    FROM flights f
                    LEFT JOIN flight_plan fp ON fp.gufi = f.gufi
                    WHERE f.aircraft_id ILIKE :q
                       OR f.departure_airport ILIKE :q
                       OR f.arrival_airport ILIKE :q
                       OR f.gufi ILIKE :q
                    ORDER BY f.aircraft_id, f.scheduled_departure DESC
                    LIMIT :limit
                """),
                {"q": f"%{q}%", "limit": limit},
            ).fetchall()

        flights = [
            {
                "ident":         r.ident,
                "origin":        r.origin,
                "destination":   r.destination,
                "aircraft_type": r.aircraft_type,
                "departure_time": r.departure_time.isoformat() if r.departure_time else None,
                "arrival_time":  None,
                "status":        r.status or "scheduled",
                "latitude":      None,
                "longitude":     None,
                "altitude":      None,
                "ground_speed":  None,
            }
            for r in rows
        ]
        return jsonify({"flights": flights, "total": len(flights)})
    except Exception as e:
        logger.exception("search_flights error")
        return jsonify({"error": str(e)}), 500


# ── Flight detail ─────────────────────────────────────────────────────
@bp.get("/<ident>")
def flight_detail(ident: str):
    try:
        with _session() as db:
            # Base flight info — join flights + flight_plan for aircraft type
            fp = db.execute(
                text("""
                    SELECT
                        f.aircraft_id,
                        f.departure_airport,
                        f.arrival_airport,
                        fp."typeOfAircraft_03c"  AS aircraft_type,
                        f.scheduled_departure,
                        f.scheduled_arrival,
                        f.current_status         AS flight_status,
                        f.gufi
                    FROM flights f
                    LEFT JOIN flight_plan fp ON fp.gufi = f.gufi
                    WHERE f.aircraft_id = :ident
                    ORDER BY f.scheduled_departure DESC
                    LIMIT 1
                """),
                {"ident": ident},
            ).fetchone()

            if not fp:
                return jsonify({"error": "Flight not found"}), 404

            # Latest position
            pos = db.execute(
                text("""
                    SELECT latitude, longitude, altitude, speed, time_at_position
                    FROM track_information
                    WHERE aircraft_id = :ident
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"ident": ident},
            ).fetchone()

            # Track: points since this flight's departure, max 500 points
            # time_at_position is varchar ISO format "2026-05-24T02:08:42Z" — lexicographic compare works
            dep_cutoff = fp.scheduled_departure.strftime('%Y-%m-%dT%H:%M:%SZ') if fp.scheduled_departure else '1970-01-01T00:00:00Z'
            track_rows = db.execute(
                text("""
                    SELECT latitude, longitude, altitude, time_at_position
                    FROM track_information
                    WHERE aircraft_id = :ident
                      AND latitude IS NOT NULL
                      AND longitude IS NOT NULL
                      AND time_at_position >= :dep_cutoff
                    ORDER BY id ASC
                    LIMIT 500
                """),
                {"ident": ident, "dep_cutoff": dep_cutoff},
            ).fetchall()

            # TBFM metering (most recent for this aircraft)
            tbfm = db.execute(
                text("""
                    SELECT airport, meter_fix, scheduled_time, delay_minutes
                    FROM tbfm_metering_flights
                    WHERE aircraft_id = :ident
                    ORDER BY scheduled_time DESC
                    LIMIT 1
                """),
                {"ident": ident},
            ).fetchone()

        track = [
            {
                "lat": _safe_float(r.latitude),
                "lon": _safe_float(r.longitude),
                "alt": _safe_int(r.altitude) or 0,
                "ts":  r.time_at_position,
            }
            for r in track_rows
            if _safe_float(r.latitude) is not None and _safe_float(r.longitude) is not None
        ]

        return jsonify({
            "ident":         fp.aircraft_id,
            "origin":        fp.departure_airport,
            "destination":   fp.arrival_airport,
            "aircraft_type": fp.aircraft_type,
            "departure_time": fp.scheduled_departure.isoformat() if fp.scheduled_departure else None,
            "arrival_time":  fp.scheduled_arrival.isoformat() if fp.scheduled_arrival else None,
            "status":        fp.flight_status or "unknown",
            "latitude":      _safe_float(pos.latitude)  if pos else None,
            "longitude":     _safe_float(pos.longitude) if pos else None,
            "altitude":      _safe_int(pos.altitude)    if pos else None,
            "ground_speed":  _safe_int(pos.speed)       if pos else None,
            "track":         track,
            "tbfm": {
                "airport":        tbfm.airport,
                "meter_fix":      tbfm.meter_fix,
                "scheduled_time": tbfm.scheduled_time.isoformat() if tbfm.scheduled_time else None,
                "delay_minutes":  tbfm.delay_minutes,
            } if tbfm else None,
        })
    except Exception as e:
        logger.exception("flight_detail error")
        return jsonify({"error": str(e)}), 500
