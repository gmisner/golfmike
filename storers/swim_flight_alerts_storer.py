"""
Store parsed SWIM rows as flight_alerts (JSONB) for message types without a dedicated fact table.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_config import SessionLocal
from storers.flight_hub import ensure_flight_hub_row, resolve_or_create_plan_gufi
from utils.logger import main_logger as logger


def _jsonable(row: Dict[str, Any]) -> str:
    def conv(v: Any) -> Any:
        if v is None or isinstance(v, (bool, int, float, str)):
            return v
        return str(v)[:20000]

    return json.dumps({k: conv(v) for k, v in row.items()})


def store_swim_rows_as_flight_alerts(
    data_list: List[Dict[str, Any]],
    msg_type: str,
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
            ensure_flight_hub_row(
                session,
                gufi,
                aid,
                flight_reference=row.get("flight_reference"),
            )
            summary = f"SWIM {msg_type} for {aid}"
            session.execute(
                text(
                    """
                    INSERT INTO flight_alerts (gufi, alert_type, severity, message, alert_data)
                    VALUES (:gufi, :atype, 'INFO', :msg, CAST(:j AS jsonb))
                """
                ),
                {
                    "gufi": gufi,
                    "atype": f"SWIM_{msg_type}",
                    "msg": summary,
                    "j": _jsonable({**row, "source_msg_type": msg_type}),
                },
            )
        if created:
            session.commit()
    except Exception as e:
        if created:
            session.rollback()
        logger.opt(exception=True).error("swim flight_alerts store failed: {}", e)
        raise
    finally:
        if created and session:
            session.close()


def store_boundary_crossing_events(
    data_list: List[Dict[str, Any]], session: Optional[Session] = None
) -> None:
    store_swim_rows_as_flight_alerts(
        data_list, "boundaryCrossingUpdate", session=session
    )


def store_oceanic_reports(
    data_list: List[Dict[str, Any]], session: Optional[Session] = None
) -> None:
    store_swim_rows_as_flight_alerts(data_list, "oceanicReport", session=session)


def store_flight_control_events(
    data_list: List[Dict[str, Any]], session: Optional[Session] = None
) -> None:
    store_swim_rows_as_flight_alerts(data_list, "FlightControl", session=session)
