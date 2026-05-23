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


# ── Active flights ────────────────────────────────────────────────────
@bp.get("/active")
def active_flights():
    limit = min(int(request.args.get("limit", 50)), 200)
    try:
        with _session() as db:
            rows = db.execute(
                text("""
                    SELECT
                        fp.aircraft_id          AS ident,
                        fp.departure_airport    AS origin,
                        fp.arrival_airport      AS destination,
                        fp.aircraft_type,
                        fp.proposed_departure_time AS departure_time,
                        fp.filed_ete            AS arrival_time,
                        COALESCE(fp.flight_status, 'active') AS status,
                        ti.latitude,
                        ti.longitude,
                        ti.altitude,
                        ti.speed                AS ground_speed
                    FROM flight_plan fp
                    LEFT JOIN LATERAL (
                        SELECT latitude, longitude, altitude, speed, time_at_position
                        FROM track_information
                        WHERE aircraft_id = fp.aircraft_id
                        ORDER BY time_at_position DESC
                        LIMIT 1
                    ) ti ON true
                    WHERE fp.flight_status NOT IN ('cancelled', 'completed', 'landed')
                      AND fp.proposed_departure_time > NOW() - INTERVAL '12 hours'
                    ORDER BY fp.proposed_departure_time DESC
                    LIMIT :limit
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
                "latitude":      float(r.latitude)    if r.latitude    is not None else None,
                "longitude":     float(r.longitude)   if r.longitude   is not None else None,
                "altitude":      int(r.altitude)      if r.altitude    is not None else None,
                "ground_speed":  int(r.ground_speed)  if r.ground_speed is not None else None,
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
                    SELECT DISTINCT ON (fp.aircraft_id)
                        fp.aircraft_id          AS ident,
                        fp.departure_airport    AS origin,
                        fp.arrival_airport      AS destination,
                        fp.aircraft_type,
                        fp.proposed_departure_time AS departure_time,
                        COALESCE(fp.flight_status, 'scheduled') AS status
                    FROM flight_plan fp
                    WHERE fp.aircraft_id ILIKE :q
                       OR fp.departure_airport ILIKE :q
                       OR fp.arrival_airport ILIKE :q
                       OR fp.gufi ILIKE :q
                    ORDER BY fp.aircraft_id, fp.proposed_departure_time DESC
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
            # Base flight info
            fp = db.execute(
                text("""
                    SELECT aircraft_id, departure_airport, arrival_airport,
                           aircraft_type, proposed_departure_time, filed_ete,
                           flight_status, gufi
                    FROM flight_plan
                    WHERE aircraft_id = :ident
                    ORDER BY proposed_departure_time DESC
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
                    ORDER BY time_at_position DESC
                    LIMIT 1
                """),
                {"ident": ident},
            ).fetchone()

            # Track (last 6 hours, max 500 points)
            track_rows = db.execute(
                text("""
                    SELECT latitude, longitude, altitude, time_at_position
                    FROM track_information
                    WHERE aircraft_id = :ident
                      AND time_at_position > NOW() - INTERVAL '6 hours'
                    ORDER BY time_at_position ASC
                    LIMIT 500
                """),
                {"ident": ident},
            ).fetchall()

            # TBFM metering (most recent)
            tbfm = db.execute(
                text("""
                    SELECT apt, scheduled_time
                    FROM tbfm_metering_flights
                    WHERE gufi LIKE :gufi_prefix
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"gufi_prefix": f"{fp.gufi}%"} if fp.gufi else {"gufi_prefix": ""},
            ).fetchone()

        track = [
            {
                "lat": float(r.latitude),
                "lon": float(r.longitude),
                "alt": int(r.altitude) if r.altitude else 0,
                "ts":  r.time_at_position.isoformat(),
            }
            for r in track_rows
            if r.latitude is not None and r.longitude is not None
        ]

        return jsonify({
            "ident":         fp.aircraft_id,
            "origin":        fp.departure_airport,
            "destination":   fp.arrival_airport,
            "aircraft_type": fp.aircraft_type,
            "departure_time": fp.proposed_departure_time.isoformat() if fp.proposed_departure_time else None,
            "arrival_time":  fp.filed_ete.isoformat() if fp.filed_ete else None,
            "status":        fp.flight_status or "unknown",
            "latitude":      float(pos.latitude)   if pos and pos.latitude   is not None else None,
            "longitude":     float(pos.longitude)  if pos and pos.longitude  is not None else None,
            "altitude":      int(pos.altitude)     if pos and pos.altitude   is not None else None,
            "ground_speed":  int(pos.speed)        if pos and pos.speed      is not None else None,
            "track":         track,
            "tbfm": {
                "apt":            tbfm.apt if tbfm else None,
                "scheduled_time": tbfm.scheduled_time.isoformat() if tbfm and tbfm.scheduled_time else None,
            } if tbfm else None,
        })
    except Exception as e:
        logger.exception("flight_detail error")
        return jsonify({"error": str(e)}), 500
