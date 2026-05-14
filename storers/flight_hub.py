"""
Central flight hub: every non-null flight_plan.gufi must reference flights(gufi).
Call ensure_flight_hub_row after aircraft exists and before inserting/updating flight_plan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Set

from sqlalchemy import text
from sqlalchemy.orm import Session
from db_config import SessionLocal
from utils.logger import main_logger as logger


def normalize_plan_gufi(gufi: Optional[str]) -> Optional[str]:
    """Single canonical form for flight_plan / flights GUFI (unique index is case-sensitive)."""
    if not gufi:
        return None
    s = str(gufi).strip()
    return s.upper() if s else None


_FLIGHTS_COLUMNS_CACHE: Optional[Set[str]] = None


def _flights_columns(session: Session) -> Set[str]:
    global _FLIGHTS_COLUMNS_CACHE
    if _FLIGHTS_COLUMNS_CACHE is not None:
        return _FLIGHTS_COLUMNS_CACHE
    rows = session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'flights'
            """
        )
    ).fetchall()
    _FLIGHTS_COLUMNS_CACHE = {r[0] for r in rows}
    return _FLIGHTS_COLUMNS_CACHE


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        logger.debug("Could not parse datetime value: {}", value)
        return None


def upsert_flight_operational_fields(
    session: Optional[Session],
    gufi: str,
    aircraft_id: str,
    fields: Dict[str, object],
) -> None:
    """
    Upsert operational fields into flights for SFDPS/NAS updates.

    Safe on older DBs: only writes columns that actually exist.
    """
    created = False
    if session is None:
        session = SessionLocal()
        created = True

    gufi = normalize_plan_gufi(gufi)
    if not gufi or not aircraft_id:
        if created:
            session.close()
        return
    try:
        known_cols = _flights_columns(session)
        values = {
            "source_timestamp": _parse_iso_dt(fields.get("source_timestamp")),
            "route_text": fields.get("route_text"),
            "current_beacon_code": fields.get("current_beacon_code"),
            "fdps_flight_status": fields.get("fdps_flight_status"),
            "coordination_time": _parse_iso_dt(fields.get("coordination_time")),
            "coordination_fix": fields.get("coordination_fix"),
            "coordination_distance_nm": fields.get("coordination_distance_nm"),
            "coordination_radial_deg": fields.get("coordination_radial_deg"),
        }
        supported = {k: v for k, v in values.items() if k in known_cols}
        if not supported:
            return

        insert_cols = ["gufi", "aircraft_id", *supported.keys(), "updated_at"]
        insert_vals = [
            ":gufi",
            ":aircraft_id",
            *[f":{k}" for k in supported.keys()],
            "NOW()",
        ]
        update_set = ",\n                ".join(
            [f"{k} = COALESCE(EXCLUDED.{k}, flights.{k})" for k in supported.keys()]
            + ["updated_at = NOW()"]
        )
        session.execute(
            text(
                f"""
                INSERT INTO flights ({", ".join(insert_cols)})
                VALUES ({", ".join(insert_vals)})
                ON CONFLICT (gufi) DO UPDATE SET
                    {update_set}
                """
            ),
            {"gufi": gufi, "aircraft_id": aircraft_id, **supported},
        )
        if created:
            session.commit()
    finally:
        if created:
            session.close()


def ensure_flight_hub_row(
    session: Session,
    gufi: str,
    aircraft_id: str,
    *,
    flight_reference: Optional[str] = None,
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    scheduled_departure: Optional[datetime] = None,
    scheduled_arrival: Optional[datetime] = None,
    current_status: str = "PLANNED",
) -> None:
    """
    Upsert into flights. Safe to call repeatedly.

    Args:
        session: Active SQLAlchemy session (caller commits).
        gufi: Flight instance identifier (PK of flights).
        aircraft_id: Tail / flight ID (must exist in aircraft).
    """
    gufi = normalize_plan_gufi(gufi)
    if not gufi or not aircraft_id:
        logger.debug("ensure_flight_hub_row skipped: missing gufi or aircraft_id")
        return

    session.execute(
        text(
            """
            INSERT INTO flights (
                gufi, aircraft_id, flight_reference, departure_airport, arrival_airport,
                scheduled_departure, scheduled_arrival, current_status, updated_at
            )
            VALUES (
                :gufi, :aircraft_id, :flight_ref, :dep, :arr,
                :sched_dep, :sched_arr, :status, NOW()
            )
            ON CONFLICT (gufi) DO UPDATE SET
                aircraft_id = EXCLUDED.aircraft_id,
                flight_reference = COALESCE(EXCLUDED.flight_reference, flights.flight_reference),
                departure_airport = COALESCE(EXCLUDED.departure_airport, flights.departure_airport),
                arrival_airport = COALESCE(EXCLUDED.arrival_airport, flights.arrival_airport),
                scheduled_departure = COALESCE(EXCLUDED.scheduled_departure, flights.scheduled_departure),
                scheduled_arrival = COALESCE(EXCLUDED.scheduled_arrival, flights.scheduled_arrival),
                current_status = EXCLUDED.current_status,
                updated_at = NOW()
            """
        ),
        {
            "gufi": gufi,
            "aircraft_id": aircraft_id,
            "flight_ref": flight_reference,
            "dep": departure_airport,
            "arr": arrival_airport,
            "sched_dep": scheduled_departure,
            "sched_arr": scheduled_arrival,
            "status": current_status,
        },
    )


def _new_temp_fp_gufi(aircraft_id: str, flight_ref: str) -> str:
    import hashlib

    ts = datetime.utcnow().isoformat()
    base = f"{aircraft_id}_{flight_ref}_{ts}"
    temp = f"TEMP_FP_{hashlib.md5(base.encode()).hexdigest()[:12].upper()}"
    logger.debug(f"Generated temporary plan GUFI {temp} for aircraft {aircraft_id}")
    return temp


def resolve_or_create_plan_gufi(
    session: Session,
    aircraft_id: str,
    flight_ref: Optional[str],
    gufi_from_message: Optional[str],
) -> Optional[str]:
    """
    Resolve GUFI for a flight plan message: message value, then DB, else a new TEMP_* id.
    """
    if gufi_from_message:
        return normalize_plan_gufi(gufi_from_message)

    if not aircraft_id:
        return None

    if flight_ref:
        row = session.execute(
            text(
                """
                SELECT gufi FROM flight_plan
                WHERE aircraft_id = :aircraft_id
                  AND flight_reference = :flight_ref
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"aircraft_id": aircraft_id, "flight_ref": flight_ref},
        ).fetchone()
        if row is not None:
            if row[0]:
                return normalize_plan_gufi(row[0])
            return _new_temp_fp_gufi(aircraft_id, flight_ref)

        row = session.execute(
            text(
                """
                SELECT gufi FROM flights
                WHERE aircraft_id = :aircraft_id
                  AND flight_reference = :flight_ref
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"aircraft_id": aircraft_id, "flight_ref": flight_ref},
        ).fetchone()
        if row and row[0]:
            return normalize_plan_gufi(row[0])

    row = session.execute(
        text(
            """
            SELECT gufi FROM flight_plan
            WHERE aircraft_id = :aircraft_id
              AND gufi IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"aircraft_id": aircraft_id},
    ).fetchone()
    if row and row[0]:
        return normalize_plan_gufi(row[0])

    return _new_temp_fp_gufi(aircraft_id, flight_ref or "")
