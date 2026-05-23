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
                    SELECT COUNT(*) AS cnt
                    FROM flight_plan
                    WHERE flight_status NOT IN ('cancelled', 'completed', 'landed')
                      AND proposed_departure_time > NOW() - INTERVAL '12 hours'
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
