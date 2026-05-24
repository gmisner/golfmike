"""
GET /v1/airports          — active airports with ITWS weather risk + traffic
GET /v1/airports/<icao>/risk — single airport risk summary
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from db_config import SessionLocal
from utils.logger import main_logger as logger

bp = Blueprint("v1_airports", __name__, url_prefix="/v1/airports")


def _session():
    return SessionLocal()


# ITWS alert type → flight category severity mapping
_ITWS_CATEGORY = {
    "ITWS_TORNADO":     "LIFR",
    "ITWS_MICROBURST":  "LIFR",
    "ITWS_GUST_FRONT":  "IFR",
    "ITWS_PRECIPITATION": "MVFR",
    "ITWS_ALERT":       "MVFR",
    "ITWS_GENERIC":     "MVFR",
}

_CAT_RANK = {"LIFR": 4, "IFR": 3, "MVFR": 2, "VFR": 1, "UNKNOWN": 0}


def _worst_category(alert_types: list[str]) -> str:
    best = "VFR"
    for t in alert_types:
        cat = _ITWS_CATEGORY.get(t, "VFR")
        if _CAT_RANK.get(cat, 0) > _CAT_RANK.get(best, 0):
            best = cat
    return best


@bp.get("")
def list_airports():
    try:
        with _session() as db:
            # Get active airports from flight traffic in last 12 hours
            traffic_rows = db.execute(text("""
                SELECT airport, SUM(cnt) AS traffic
                FROM (
                    SELECT departure_airport AS airport, COUNT(*) AS cnt
                    FROM flights
                    WHERE current_status IN ('ACTIVE', 'IN_FLIGHT', 'PLANNED')
                      AND scheduled_departure > NOW() - INTERVAL '12 hours'
                      AND departure_airport IS NOT NULL
                    GROUP BY departure_airport
                    UNION ALL
                    SELECT arrival_airport AS airport, COUNT(*) AS cnt
                    FROM flights
                    WHERE current_status IN ('ACTIVE', 'IN_FLIGHT', 'PLANNED')
                      AND scheduled_departure > NOW() - INTERVAL '12 hours'
                      AND arrival_airport IS NOT NULL
                    GROUP BY arrival_airport
                ) t
                GROUP BY airport
                ORDER BY traffic DESC
                LIMIT 50
            """)).fetchall()

            airports_icao = [r.airport for r in traffic_rows]
            if not airports_icao:
                return jsonify({"airports": []})

            # Get active weather alerts — alerts use 3-letter IATA, flights use 4-letter ICAO
            # Match by stripping leading K from ICAO codes
            iata_codes = [a[1:] if a.startswith('K') and len(a) == 4 else a for a in airports_icao]
            alert_rows = db.execute(text("""
                SELECT wa.alert_type, apt.airport
                FROM weather_alerts wa
                CROSS JOIN LATERAL jsonb_array_elements_text(wa.affected_airports) AS apt(airport)
                WHERE wa.is_active = true
                  AND wa.valid_from > NOW() - INTERVAL '6 hours'
                  AND (wa.valid_until IS NULL OR wa.valid_until > NOW())
                  AND jsonb_typeof(wa.affected_airports) = 'array'
                  AND apt.airport = ANY(:iata_codes)
            """), {"iata_codes": iata_codes}).fetchall()

        # Build alert map keyed by IATA code (3-letter)
        alert_map: dict[str, list[str]] = {}
        for r in alert_rows:
            alert_map.setdefault(r.airport, []).append(r.alert_type)

        # Build traffic map
        traffic_map = {r.airport: int(r.traffic) for r in traffic_rows}

        airports = []
        for icao in airports_icao:
            iata = icao[1:] if icao.startswith('K') and len(icao) == 4 else icao
            alert_types = alert_map.get(iata, [])
            category = _worst_category(alert_types)
            airports.append({
                "icao":         icao,
                "iata":         icao,   # use same until we have a mapping table
                "name":         icao,
                "category":     category,
                "alert_count":  len(alert_types),
                "alert_types":  list(set(alert_types)),
                "traffic":      traffic_map.get(icao, 0),
                # METAR fields — empty until weather feed comes online
                "ceiling":      None,
                "visibility":   None,
                "wind_speed":   None,
                "wind_dir":     None,
                "raw_metar":    None,
                "observed":     None,
            })

        return jsonify({"airports": airports})
    except Exception as e:
        logger.exception("list_airports error")
        return jsonify({"error": str(e)}), 500


@bp.get("/<icao>/risk")
def airport_risk(icao: str):
    icao = icao.upper()
    try:
        with _session() as db:
            # Try METAR first
            metar = None
            try:
                metar = db.execute(text("""
                    SELECT station_id, observation_time, raw_text,
                           wind_direction, wind_speed,
                           visibility::text AS visibility,
                           flight_category, sky_conditions
                    FROM metar_data
                    WHERE station_id = :icao
                    ORDER BY observation_time DESC
                    LIMIT 1
                """), {"icao": icao}).fetchone()
            except Exception:
                pass

            if metar:
                ceiling = None
                try:
                    import json
                    sky = json.loads(metar.sky_conditions) if isinstance(metar.sky_conditions, str) else metar.sky_conditions
                    if isinstance(sky, list):
                        for layer in sky:
                            if (layer.get("sky_cover") or "").upper() in ("BKN", "OVC", "OVX"):
                                h = layer.get("cloud_base_ft_agl")
                                if h:
                                    ceiling = int(h)
                                    break
                except Exception:
                    pass
                return jsonify({
                    "icao":       metar.station_id,
                    "iata":       metar.station_id,
                    "name":       metar.station_id,
                    "category":   (metar.flight_category or "UNKNOWN").upper(),
                    "ceiling":    ceiling,
                    "visibility": metar.visibility,
                    "wind_speed": metar.wind_speed,
                    "wind_dir":   metar.wind_direction,
                    "raw_metar":  metar.raw_text,
                    "observed":   metar.observation_time.isoformat() if metar.observation_time else None,
                })

            # Fall back to ITWS alerts
            alerts = db.execute(text("""
                SELECT alert_type FROM weather_alerts
                WHERE is_active = true
                  AND valid_until > NOW() - INTERVAL '2 hours'
                  AND affected_airports ? :icao
            """), {"icao": icao}).fetchall()

        alert_types = [r.alert_type for r in alerts]
        return jsonify({
            "icao":       icao,
            "iata":       icao,
            "name":       icao,
            "category":   _worst_category(alert_types),
            "alert_count": len(alert_types),
            "alert_types": list(set(alert_types)),
            "ceiling":    None,
            "visibility": None,
            "wind_speed": None,
            "wind_dir":   None,
            "raw_metar":  None,
            "observed":   None,
        })
    except Exception as e:
        logger.exception("airport_risk error")
        return jsonify({"error": str(e)}), 500
