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
            # Try flight_events table first
            rows = db.execute(
                text("""
                    SELECT id, event_type, aircraft_id AS ident,
                           airport_code AS airport,
                           event_time AS ts,
                           COALESCE(message, event_type || ' ' || aircraft_id) AS message
                    FROM flight_events
                    ORDER BY event_time DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()

        events = [
            {
                "id":         r.id,
                "event_type": r.event_type,
                "ident":      r.ident,
                "airport":    r.airport,
                "ts":         r.ts.isoformat() if r.ts else None,
                "message":    r.message,
            }
            for r in rows
        ]
        return jsonify({"events": events})
    except Exception as e:
        logger.exception("recent_events error")
        return jsonify({"events": [], "error": str(e)}), 200  # soft fail — feed just stays empty
