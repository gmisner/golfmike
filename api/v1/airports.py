"""
GET /v1/airports          — all tracked airports with flight category
GET /v1/airports/<icao>/risk — single airport risk summary
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_airports", __name__, url_prefix="/v1/airports")


def _session():
    return SessionLocal()


def _category(ceiling, visibility) -> str:
    """Derive VFR/MVFR/IFR/LIFR from ceiling (ft) and visibility (sm)."""
    if ceiling is None and visibility is None:
        return "UNKNOWN"
    ceil = ceiling if ceiling is not None else 99999
    vis  = float(visibility) if visibility is not None else 99.0
    if ceil < 500 or vis < 1:
        return "LIFR"
    if ceil < 1000 or vis < 3:
        return "IFR"
    if ceil < 3000 or vis < 5:
        return "MVFR"
    return "VFR"


def _metar_row_to_airport(row) -> dict:
    # Pull ceiling from sky_conditions JSON if present
    ceiling = None
    try:
        import json
        sky = json.loads(row.sky_conditions) if isinstance(row.sky_conditions, str) else row.sky_conditions
        if isinstance(sky, list):
            for layer in sky:
                cov = (layer.get("sky_cover") or "").upper()
                if cov in ("BKN", "OVC", "OVX"):
                    h = layer.get("cloud_base_ft_agl")
                    if h:
                        ceiling = int(h)
                        break
    except Exception:
        pass

    try:
        vis = float(row.visibility) if row.visibility is not None else None
    except (TypeError, ValueError):
        vis = None

    category = row.flight_category or _category(ceiling, vis)

    return {
        "icao":       row.station_id,
        "iata":       None,
        "name":       row.station_id,
        "category":   category.upper() if category else "UNKNOWN",
        "ceiling":    ceiling,
        "visibility": vis,
        "wind_speed": row.wind_speed,
        "wind_dir":   row.wind_direction,
        "raw_metar":  row.raw_text,
        "observed":   row.observation_time.isoformat() if row.observation_time else None,
    }


@bp.get("")
def list_airports():
    try:
        rows = []
        with _session() as db:
            for table in ("metar_data_api", "metar_data"):
                try:
                    rows = db.execute(
                        text(f"""
                            SELECT DISTINCT ON (station_id)
                                station_id, observation_time, raw_text,
                                wind_direction, wind_speed,
                                visibility::text AS visibility,
                                flight_category, sky_conditions
                            FROM {table}
                            WHERE observation_time > NOW() - INTERVAL '3 hours'
                            ORDER BY station_id, observation_time DESC
                            LIMIT 50
                        """)
                    ).fetchall()
                    if rows:
                        break
                except Exception:
                    continue

        airports = [_metar_row_to_airport(r) for r in rows]
        return jsonify({"airports": airports})
    except Exception as e:
        logger.exception("list_airports error")
        return jsonify({"error": str(e)}), 500


@bp.get("/<icao>/risk")
def airport_risk(icao: str):
    icao = icao.upper()
    try:
        with _session() as db:
            row = None
            for table in ("metar_data_api", "metar_data"):
                try:
                    row = db.execute(
                        text(f"""
                            SELECT station_id, observation_time, raw_text,
                                   wind_direction, wind_speed,
                                   visibility::text AS visibility,
                                   flight_category, sky_conditions
                            FROM {table}
                            WHERE station_id = :icao
                            ORDER BY observation_time DESC
                            LIMIT 1
                        """),
                        {"icao": icao},
                    ).fetchone()
                    if row:
                        break
                except Exception:
                    continue

        if not row:
            return jsonify({"icao": icao, "category": "UNKNOWN"}), 404

        return jsonify(_metar_row_to_airport(row))
    except Exception as e:
        logger.exception("airport_risk error")
        return jsonify({"error": str(e)}), 500
