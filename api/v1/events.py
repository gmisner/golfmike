"""
GET /v1/events/recent — latest flight events (departures, arrivals, etc.)
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_events", __name__, url_prefix="/v1/events")


def _session():
    return SessionLocal()


@bp.get("/recent")
def recent_events():
    limit = min(int(request.args.get("limit", 30)), 100)
    try:
        with _session() as db:
            rows = db.execute(
                text("""
                    SELECT
                        fe.id,
                        fe.event_type,
                        fe.aircraft_id                          AS ident,
                        fe.event_timestamp                      AS ts,
                        fe.source_facility                      AS facility,
                        fe.event_data,
                        f.departure_airport                     AS origin,
                        f.arrival_airport                       AS destination
                    FROM flight_events fe
                    LEFT JOIN flights f ON f.gufi = fe.gufi
                    ORDER BY fe.event_timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()

        def _label(event_type: str, data: dict | None) -> str:
            t = (event_type or "").upper()
            if t in ("DEPARTURE", "DEPARTED"):
                return "Departed"
            if t in ("ARRIVAL", "ARRIVED", "LANDED"):
                return "Arrived"
            if t in ("FILED", "FLIGHT_PLAN", "FLIGHT_PLAN_FILED"):
                return "Filed"
            if t in ("CANCELLED", "CANCELED"):
                return "Cancelled"
            if t in ("DIVERTED", "DIVERSION"):
                return "Diverted"
            return event_type.replace("_", " ").title() if event_type else "Event"

        events = []
        for r in rows:
            data = r.event_data or {}
            events.append({
                "id":         r.id,
                "event_type": r.event_type,
                "label":      _label(r.event_type, data),
                "ident":      r.ident,
                "origin":     r.origin or data.get("departure_airport"),
                "destination": r.destination or data.get("arrival_airport"),
                "facility":   r.facility,
                "ts":         r.ts.isoformat() if r.ts else None,
            })

        return jsonify({"events": events})
    except Exception as e:
        logger.exception("recent_events error")
        return jsonify({"events": [], "error": str(e)}), 200  # soft fail
