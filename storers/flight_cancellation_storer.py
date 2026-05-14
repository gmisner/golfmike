"""Set flights.current_status = CANCELLED for cancellation messages."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from db_config import SessionLocal
from storers.flight_hub import ensure_flight_hub_row, resolve_or_create_plan_gufi
from utils.logger import main_logger as logger


def store_flight_plan_cancellations(
    data_list: List[Dict[str, Any]], session: Optional[Session] = None
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
                current_status="CANCELLED",
            )
        if created:
            session.commit()
    except Exception as e:
        if created:
            session.rollback()
        logger.opt(exception=True).error("flight plan cancellation store failed: {}", e)
        raise
    finally:
        if created and session:
            session.close()
