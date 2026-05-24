"""
GET /v1/status — live connection status + flight count for the navbar indicator
"""

from flask import Blueprint, jsonify
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_status", __name__, url_prefix="/v1")


def _session():
    return SessionLocal()


@bp.get("/status")
def status():
    try:
        with _session() as db:
            row = db.execute(
                text("""
                    SELECT COUNT(DISTINCT f.aircraft_id) AS cnt
                    FROM flights f
                    INNER JOIN track_information ti ON ti.aircraft_id = f.aircraft_id
                    WHERE f.current_status IN ('ACTIVE', 'IN_FLIGHT')
                      AND ti.time_at_position > TO_CHAR(NOW() - INTERVAL '2 hours',
                                                        'YYYY-MM-DD"T"HH24:MI:SS"Z"')
                """)
            ).fetchone()
            flight_count = row.cnt if row else 0

        return jsonify({
            "connected":    True,
            "flight_count": int(flight_count),
        })
    except Exception as e:
        logger.exception("status error")
        return jsonify({"connected": False, "flight_count": 0})
