"""
Flow control probability service.

Answers: "What is the probability that FAA will impose flow control at
<airport> in the next <N> hours?"

Architecture
────────────
v1 (this file) — Expert heuristic scorer
  Uses weighted risk factors derived from aviation operations knowledge.
  Deployable immediately with zero training data.
  Every prediction is stored with its feature snapshot so that once
  ~6 months of labeled data accumulate, v2 can train an ML model on it.

v2 (future) — scikit-learn / XGBoost model
  Features: same feature dict produced here.
  Label: FlowPredictionDBModel.actual_flow_control (filled retrospectively
         by a Celery beat task that cross-references TMI records).
  Drop-in replacement for score_flow_probability().

Risk factors (additive, capped at 0.98)
──────────────────────────────────────
 BASE                      0.04   always-on baseline
 LIFR ceiling/vis          0.55   ceiling < 200ft OR vis < 0.25sm
 IFR ceiling/vis           0.35   ceiling < 1000ft OR vis < 3sm
 MVFR ceiling/vis          0.12   ceiling < 3000ft OR vis < 5sm
 Wind gust > 40kt          0.25
 Wind gust 30–40kt         0.12
 Active SIGMET nearby      0.30   any active SIGMET affecting airport
 Active AIRMET Sierra      0.18   IFR conditions AIRMET
 Active AIRMET Tango       0.10   turbulence AIRMET
 TAF deteriorating         0.20   forecast ceiling/vis worsening next 2h
 Active GDP (TMI)          0.50   ground delay program already running
 Active GS  (TMI)          0.70   ground stop already running
 Active MIT (TMI)          0.20   miles-in-trail restriction
 High arrival demand       0.12   >25 arrivals in last hour
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.sqlalchemy.flow_prediction import FlowPredictionDBModel
from utils.logger import main_logger as logger


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_visibility(vis_str: Optional[str]) -> Optional[float]:
    """Convert METAR visibility string to a float in statute miles."""
    if not vis_str:
        return None
    s = str(vis_str).strip().replace("+", "")
    try:
        return float(s)
    except ValueError:
        pass
    # Handle fractions like "1/4", "1 1/2"
    parts = s.split()
    total = 0.0
    for part in parts:
        if "/" in part:
            n, d = part.split("/", 1)
            try:
                total += float(n) / float(d)
            except (ValueError, ZeroDivisionError):
                pass
        else:
            try:
                total += float(part)
            except ValueError:
                pass
    return total if total > 0 else None


def _extract_ceiling(sky_conditions: Optional[List[Dict]]) -> Optional[int]:
    """Return the lowest BKN or OVC layer base in feet, or None if clear."""
    if not sky_conditions:
        return None
    ceiling = None
    for layer in sky_conditions:
        cover = str(layer.get("cover", "")).upper()
        if cover in ("BKN", "OVC"):
            base = layer.get("base")
            try:
                base = int(base)
                if ceiling is None or base < ceiling:
                    ceiling = base
            except (TypeError, ValueError):
                pass
    return ceiling


def _risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "VERY_HIGH"
    if probability >= 0.55:
        return "HIGH"
    if probability >= 0.35:
        return "MODERATE"
    if probability >= 0.15:
        return "LOW"
    return "VERY_LOW"


def _sigmoid_blend(raw_score: float) -> float:
    """Smooth the additive score through a sigmoid so it reads as a probability."""
    return 1 / (1 + math.exp(-6 * (raw_score - 0.5)))


# ── Feature extraction ────────────────────────────────────────────────────────

def _fetch_metar(airport_icao: str, session: Session) -> Dict[str, Any]:
    """Pull the most recent METAR for this airport."""
    row = session.execute(
        text(
            """
            SELECT wind_speed, wind_gust, visibility, flight_category,
                   sky_conditions, temperature, dewpoint, observation_time
            FROM metar_data_api
            WHERE station_id = :icao
            ORDER BY observation_time DESC
            LIMIT 1
            """
        ),
        {"icao": airport_icao},
    ).fetchone()

    if not row:
        return {}

    sky = row.sky_conditions or []
    return {
        "wind_speed_kt": row.wind_speed,
        "wind_gust_kt": row.wind_gust,
        "visibility_sm": _parse_visibility(row.visibility),
        "flight_category": row.flight_category,
        "ceiling_ft": _extract_ceiling(sky),
        "sky_conditions": sky,
        "observation_time": row.observation_time,
    }


def _fetch_taf_trend(airport_icao: str, window_hours: int, session: Session) -> str:
    """
    Assess whether the TAF shows improving, deteriorating, or steady conditions
    over the next window_hours by comparing current forecast period to the last.
    Returns: IMPROVING / STEADY / DETERIORATING
    """
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=window_hours)

    rows = session.execute(
        text(
            """
            SELECT forecast_periods
            FROM taf_data_api
            WHERE station_id = :icao
              AND valid_from <= :future
              AND valid_to >= :now
            ORDER BY issue_time DESC
            LIMIT 1
            """
        ),
        {"icao": airport_icao, "now": now, "future": future},
    ).fetchone()

    if not rows or not rows.forecast_periods:
        return "STEADY"

    periods = rows.forecast_periods
    if not isinstance(periods, list) or len(periods) < 2:
        return "STEADY"

    # Compare ceiling in first period vs last period of the window
    def _period_ceiling(p):
        return _extract_ceiling(p.get("sky_conditions", []))

    first_ceil = _period_ceiling(periods[0])
    last_ceil = _period_ceiling(periods[-1])

    if first_ceil is None or last_ceil is None:
        return "STEADY"
    if last_ceil < first_ceil - 800:
        return "DETERIORATING"
    if last_ceil > first_ceil + 800:
        return "IMPROVING"
    return "STEADY"


def _fetch_active_sigmets_airmets(airport_icao: str, session: Session) -> Dict[str, bool]:
    """Check for active SIGMETs and AIRMETs affecting this airport."""
    now = datetime.now(timezone.utc)
    rows = session.execute(
        text(
            """
            SELECT alert_type, severity, weather_phenomena
            FROM weather_alerts_api
            WHERE is_active = true
              AND is_cancelled = false
              AND valid_from <= :now
              AND valid_until >= :now
              AND (
                affected_airports ? :icao
                OR affected_airports IS NULL
              )
            """
        ),
        {"icao": airport_icao, "now": now},
    ).fetchall()

    result = {
        "active_sigmet": False,
        "active_airmet_sierra": False,
        "active_airmet_tango": False,
    }

    for row in rows:
        alert_type = str(row.alert_type).upper()
        phenomena = row.weather_phenomena or {}
        if "SIGMET" in alert_type:
            result["active_sigmet"] = True
        if "AIRMET" in alert_type:
            phenomena_str = str(phenomena).upper()
            if "SIERRA" in phenomena_str or "IFR" in phenomena_str or "MTN OBSCN" in phenomena_str:
                result["active_airmet_sierra"] = True
            if "TANGO" in phenomena_str or "TURB" in phenomena_str:
                result["active_airmet_tango"] = True

    return result


def _fetch_tmi_status(airport_icao: str, session: Session) -> List[str]:
    """
    Detect active TMI programs touching this airport by inspecting recent
    tmi_updates. The fca_name field typically contains the airport ICAO
    and program type (e.g. 'KJFK GDP', 'KLAX GS').
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    rows = session.execute(
        text(
            """
            SELECT DISTINCT update_type, fca_id
            FROM tmi_updates
            WHERE update_time >= :cutoff
              AND (
                fca_id ILIKE :icao_pattern
                OR fca_id ILIKE :icao_pattern2
              )
            """
        ),
        {
            "cutoff": cutoff,
            "icao_pattern": f"%{airport_icao}%",
            "icao_pattern2": f"%{airport_icao[1:]}%",  # also match without K prefix
        },
    ).fetchall()

    # Also check tmi_flight_list for flights entering an FCA named after this airport
    tmi_rows = session.execute(
        text(
            """
            SELECT DISTINCT fca_name
            FROM tmi_flight_list
            WHERE update_time >= :cutoff
              AND fca_name ILIKE :pattern
            """
        ),
        {"cutoff": cutoff, "pattern": f"%{airport_icao}%"},
    ).fetchall()

    active = set()
    for row in rows:
        utype = str(row.update_type or "").upper()
        for prog in ("GDP", "GS", "MIT", "AFP", "EDCT"):
            if prog in utype:
                active.add(prog)

    for row in tmi_rows:
        name = str(row.fca_name or "").upper()
        for prog in ("GDP", "GS", "MIT", "AFP", "EDCT"):
            if prog in name:
                active.add(prog)

    return sorted(active)


def _fetch_arrival_count(airport_icao: str, session: Session) -> int:
    """Count active tracks with this airport as destination in the last hour."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    row = session.execute(
        text(
            """
            SELECT COUNT(*) as cnt
            FROM track_information
            WHERE arrival_airport = :icao
              AND time_at_position >= :cutoff
            """
        ),
        {"icao": airport_icao, "cutoff": str(cutoff)},
    ).fetchone()
    return row.cnt if row else 0


# ── Scorer ────────────────────────────────────────────────────────────────────

def score_flow_probability(features: Dict[str, Any]) -> Tuple[float, List[Dict]]:
    """
    Apply weighted heuristic scoring to a feature dict.
    Returns (probability_0_to_1, risk_factors_list).

    This function is the v1 implementation. When enough labeled data
    accumulates in FlowPredictionDBModel, replace this with a trained
    scikit-learn model that takes the same feature dict as input.
    """
    score = 0.04  # baseline — any airport has ~4% baseline flow risk
    factors: List[Dict] = []

    def _add(factor: str, contribution: float, description: str) -> None:
        nonlocal score
        if contribution > 0:
            score += contribution
            factors.append(
                {
                    "factor": factor,
                    "contribution": round(contribution, 3),
                    "description": description,
                }
            )

    # ── Active TMI (highest weight — program already running) ─────────────────
    tmi_types = features.get("active_tmi_types") or []
    if "GS" in tmi_types:
        _add("ACTIVE_GROUND_STOP", 0.70, "Ground Stop active — departures halted")
    if "GDP" in tmi_types:
        _add("ACTIVE_GDP", 0.50, "Ground Delay Program active — delays being assigned")
    if "MIT" in tmi_types:
        _add("ACTIVE_MIT", 0.20, "Miles-In-Trail restriction active")
    if "AFP" in tmi_types or "EDCT" in tmi_types:
        _add("ACTIVE_AFP_EDCT", 0.20, "Airspace Flow Program / EDCT program active")

    # ── Flight category / weather ─────────────────────────────────────────────
    category = (features.get("flight_category") or "").upper()
    ceiling = features.get("ceiling_ft")
    vis = features.get("visibility_sm")

    if category == "LIFR" or (ceiling is not None and ceiling < 200) or (vis is not None and vis < 0.25):
        _add(
            "FLIGHT_CATEGORY_LIFR",
            0.55,
            f"LIFR conditions — ceiling {ceiling}ft, visibility {vis}sm",
        )
    elif category == "IFR" or (ceiling is not None and ceiling < 1000) or (vis is not None and vis < 3.0):
        _add(
            "FLIGHT_CATEGORY_IFR",
            0.35,
            f"IFR conditions — ceiling {ceiling}ft, visibility {vis}sm",
        )
    elif category == "MVFR" or (ceiling is not None and ceiling < 3000) or (vis is not None and vis < 5.0):
        _add(
            "FLIGHT_CATEGORY_MVFR",
            0.12,
            f"MVFR conditions — ceiling {ceiling}ft, visibility {vis}sm",
        )

    # ── Wind ─────────────────────────────────────────────────────────────────
    gust = features.get("wind_gust_kt") or 0
    wind = features.get("wind_speed_kt") or 0
    effective_wind = max(gust, wind)
    if effective_wind >= 40:
        _add("WIND_SEVERE", 0.25, f"Severe winds — {effective_wind}kt gusts")
    elif effective_wind >= 30:
        _add("WIND_STRONG", 0.12, f"Strong winds — {effective_wind}kt gusts")

    # ── SIGMETs / AIRMETs ────────────────────────────────────────────────────
    if features.get("active_sigmet"):
        _add("ACTIVE_SIGMET", 0.30, "SIGMET active affecting this airport or vicinity")
    if features.get("active_airmet_sierra"):
        _add("AIRMET_SIERRA", 0.18, "AIRMET Sierra — IFR conditions or mountain obscuration")
    if features.get("active_airmet_tango"):
        _add("AIRMET_TANGO", 0.10, "AIRMET Tango — moderate turbulence")

    # ── TAF trend ────────────────────────────────────────────────────────────
    trend = features.get("taf_trend", "STEADY")
    if trend == "DETERIORATING":
        _add("TAF_DETERIORATING", 0.20, "Forecast shows deteriorating conditions in window")
    elif trend == "IMPROVING":
        score = max(0.04, score - 0.10)  # improving conditions reduce overall risk
        factors.append(
            {
                "factor": "TAF_IMPROVING",
                "contribution": -0.10,
                "description": "Forecast shows improving conditions — risk reduced",
            }
        )

    # ── Arrival demand ────────────────────────────────────────────────────────
    arrivals = features.get("arrival_count_1h") or 0
    if arrivals > 25:
        _add("HIGH_ARRIVAL_DEMAND", 0.12, f"High arrival demand — {arrivals} tracks in last hour")

    # ── Apply sigmoid to smooth the additive total ────────────────────────────
    probability = round(min(max(_sigmoid_blend(score), 0.02), 0.98), 3)

    # Sort factors by contribution magnitude descending
    factors.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    return probability, factors


# ── Confidence ────────────────────────────────────────────────────────────────

def _assess_confidence(features: Dict[str, Any]) -> str:
    data_sources = features.get("data_sources", [])
    if "METAR" in data_sources and "TMI" in data_sources:
        return "HIGH"
    if "METAR" in data_sources or "TMI" in data_sources:
        return "MEDIUM"
    return "LOW"


# ── Public entry point ────────────────────────────────────────────────────────

def predict_flow_probability(
    airport_icao: str,
    window_hours: int = 2,
    session: Optional[Session] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Generate a flow control probability prediction for an airport.

    Args:
        airport_icao:  ICAO airport code (e.g. "KJFK")
        window_hours:  Forecast horizon in hours (1–6)
        session:       SQLAlchemy session (opens one internally if None)
        persist:       Whether to store the prediction in flow_predictions table

    Returns:
        Full prediction dict ready to return as a JSON API response.
    """
    from db_config import SessionLocal

    own_session = session is None
    if own_session:
        session = SessionLocal()

    try:
        icao = airport_icao.upper()
        data_sources: List[str] = []

        # ── Gather features ───────────────────────────────────────────────────
        metar = _fetch_metar(icao, session)
        if metar:
            data_sources.append("METAR")

        taf_trend = _fetch_taf_trend(icao, window_hours, session)
        if taf_trend != "STEADY" or True:  # always attempt TAF
            data_sources.append("TAF")

        alerts = _fetch_active_sigmets_airmets(icao, session)
        if any(alerts.values()):
            data_sources.append("SIGMET/AIRMET")

        tmi_types = _fetch_tmi_status(icao, session)
        if tmi_types:
            data_sources.append("TMI")

        arrival_count = _fetch_arrival_count(icao, session)
        if arrival_count > 0:
            data_sources.append("TRACK_COUNT")

        features = {
            "airport_icao": icao,
            "window_hours": window_hours,
            "ceiling_ft": metar.get("ceiling_ft"),
            "visibility_sm": metar.get("visibility_sm"),
            "flight_category": metar.get("flight_category"),
            "wind_speed_kt": metar.get("wind_speed_kt"),
            "wind_gust_kt": metar.get("wind_gust_kt"),
            "taf_trend": taf_trend,
            "active_tmi_types": tmi_types,
            "active_sigmet": alerts.get("active_sigmet", False),
            "active_airmet_sierra": alerts.get("active_airmet_sierra", False),
            "active_airmet_tango": alerts.get("active_airmet_tango", False),
            "arrival_count_1h": arrival_count,
            "data_sources": data_sources,
        }

        # ── Score ─────────────────────────────────────────────────────────────
        probability, risk_factors = score_flow_probability(features)
        risk_lvl = _risk_level(probability)
        confidence = _assess_confidence(features)

        now = datetime.now(timezone.utc)

        # ── Persist ───────────────────────────────────────────────────────────
        if persist:
            try:
                prediction = FlowPredictionDBModel(
                    airport_icao=icao,
                    predicted_at=now,
                    window_hours=window_hours,
                    flow_probability=probability,
                    risk_level=risk_lvl,
                    confidence=confidence,
                    ceiling_ft=features.get("ceiling_ft"),
                    visibility_sm=features.get("visibility_sm"),
                    flight_category=features.get("flight_category"),
                    wind_speed_kt=features.get("wind_speed_kt"),
                    wind_gust_kt=features.get("wind_gust_kt"),
                    taf_trend=taf_trend,
                    active_tmi_types=tmi_types,
                    active_sigmet=alerts.get("active_sigmet", False),
                    active_airmet_sierra=alerts.get("active_airmet_sierra", False),
                    active_airmet_tango=alerts.get("active_airmet_tango", False),
                    arrival_count_1h=arrival_count,
                    risk_factors=risk_factors,
                    feature_snapshot=features,
                )
                session.add(prediction)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.warning(f"Could not persist flow prediction for {icao}: {e}")

        # ── Build response ────────────────────────────────────────────────────
        metar_obs_time = metar.get("observation_time")
        return {
            "airport": icao,
            "predicted_at": now.isoformat(),
            "window_hours": window_hours,
            "window_ends_at": (now + timedelta(hours=window_hours)).isoformat(),
            "flow_probability": probability,
            "risk_level": risk_lvl,
            "confidence": confidence,
            "risk_factors": risk_factors,
            "current_conditions": {
                "flight_category": features.get("flight_category"),
                "ceiling_ft": features.get("ceiling_ft"),
                "visibility_sm": features.get("visibility_sm"),
                "wind_speed_kt": features.get("wind_speed_kt"),
                "wind_gust_kt": features.get("wind_gust_kt"),
                "active_tmi": tmi_types,
                "taf_trend": taf_trend,
                "metar_age_minutes": (
                    round((now - metar_obs_time.replace(tzinfo=timezone.utc)).total_seconds() / 60)
                    if metar_obs_time else None
                ),
            },
            "data_sources": data_sources,
            "model_version": "heuristic-v1",
        }

    finally:
        if own_session:
            session.close()


def batch_predict(
    airport_icao_list: List[str],
    window_hours: int = 2,
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Run predictions for multiple airports, sorted by probability descending."""
    from db_config import SessionLocal

    own_session = session is None
    if own_session:
        session = SessionLocal()

    try:
        results = []
        for icao in airport_icao_list:
            try:
                result = predict_flow_probability(icao, window_hours, session, persist=True)
                results.append(result)
            except Exception as e:
                logger.error(f"Flow prediction failed for {icao}: {e}")
                results.append(
                    {
                        "airport": icao.upper(),
                        "error": str(e),
                        "flow_probability": None,
                    }
                )

        results.sort(
            key=lambda x: x.get("flow_probability") or 0,
            reverse=True,
        )
        return results

    finally:
        if own_session:
            session.close()
