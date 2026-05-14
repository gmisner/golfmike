"""
Persist TFM departureInformation: update flights hub (actual/estimated times, status).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_config import SessionLocal
from storers.flight_hub import ensure_flight_hub_row, resolve_or_create_plan_gufi
from utils.logger import main_logger as logger


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    s = str(dt_str).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            logger.warning("Could not parse datetime: {}", s)
    return None


def store_departure_information(
    data_list: List[Dict[str, Any]],
    session: Optional[Session] = None,
) -> None:
    if not data_list:
        return
    created = session is None
    if created:
        session = SessionLocal()
    if not isinstance(session, Session):
        raise TypeError("session must be a SQLAlchemy Session")
    try:
        for row in data_list:
            aid = row.get("aircraft_id")
            if not aid:
                continue
            gufi = resolve_or_create_plan_gufi(
                session, aid, row.get("flight_reference"), row.get("gufi")
            )
            if not gufi:
                logger.warning("departureInformation: no gufi for {}", aid)
                continue

            session.execute(
                text(
                    """
                    INSERT INTO aircraft (aircraft_id) VALUES (:a)
                    ON CONFLICT (aircraft_id) DO NOTHING
                """
                ),
                {"a": aid},
            )

            dep_t = _parse_dt(row.get("etd_time"))
            if dep_t is None:
                dep_t = _parse_dt(row.get("time_of_departure"))
            arr_t = _parse_dt(row.get("eta_time"))

            ensure_flight_hub_row(
                session,
                gufi,
                aid,
                flight_reference=row.get("flight_reference"),
                departure_airport=row.get("departure_airport"),
                arrival_airport=row.get("arrival_airport"),
                scheduled_departure=dep_t,
                scheduled_arrival=arr_t,
                current_status="IN_FLIGHT",
            )
            logger.info(
                "departureInformation stored: gufi={} aircraft={} dep={} arr={}",
                gufi,
                aid,
                dep_t,
                arr_t,
            )
        if created:
            session.commit()
    except Exception as e:
        if created:
            session.rollback()
        logger.opt(exception=True).error("Error storing departure information: {}", e)
        raise
    finally:
        if created and session:
            session.close()
