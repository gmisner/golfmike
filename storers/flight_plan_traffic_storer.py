"""
Flight Plan Storer for Traffic Consumer
Stores flight plan data to flight_plan table and creates/updates flights table entries
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from db_config import SessionLocal
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger
from typing import List, Dict, Any
from datetime import datetime
from services.gufi_resolver import auto_resolve_gufi_on_flight_plan_store
from storers.flight_hub import ensure_flight_hub_row, resolve_or_create_plan_gufi

# PostgreSQL folds unquoted identifiers to lowercase; SQLAlchemy created these as quoted mixed-case.
FP_ROUTE_COL = '"flightPlanRoute_10a"'
FP_FLIGHT_ID_COL = '"flightId_02a"'


def _parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        if isinstance(dt_str, datetime):
            return dt_str
        return datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"]:
                return datetime.strptime(str(dt_str), fmt)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {dt_str}")
            return None


def store_flight_plan_traffic(
    flight_plan_data_list: List[Dict[str, Any]], session: Session = None
) -> None:
    """
    Store flight plan data from traffic consumer

    Args:
        flight_plan_data_list: List of parsed flight plan dictionaries
        session: Database session (optional)
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True
    elif not isinstance(session, Session):
        logger.error(
            "Invalid session type: {}. Expected <class 'sqlalchemy.orm.session.Session'>.",
            type(session),
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    try:
        for flight_plan_data in flight_plan_data_list:
            aircraft_id = normalize_aircraft_id(flight_plan_data.get("aircraft_id"))
            if aircraft_id:
                flight_plan_data["aircraft_id"] = aircraft_id
            gufi = flight_plan_data.get("gufi")
            flight_ref = flight_plan_data.get("flight_reference")

            if not aircraft_id:
                logger.warning("⚠️ No aircraft_id in flight plan data, skipping")
                continue

            logger.info(
                f"💾 Storing flight plan: Aircraft={aircraft_id}, GUFI={gufi}, Ref={flight_ref}"
            )

            # Ensure aircraft exists (required for foreign key constraints)
            session.execute(
                text(
                    """
                    INSERT INTO aircraft (aircraft_id)
                    VALUES (:aircraft_id)
                    ON CONFLICT (aircraft_id) DO NOTHING
                """
                ),
                {"aircraft_id": aircraft_id},
            )
            logger.debug(f"Ensured aircraft {aircraft_id} exists in aircraft table")

            igtd = _parse_dt(flight_plan_data.get("igtd"))

            gufi = resolve_or_create_plan_gufi(session, aircraft_id, flight_ref, gufi)
            if not gufi:
                logger.warning(f"No GUFI resolved for aircraft {aircraft_id}, skipping")
                continue

            ensure_flight_hub_row(
                session,
                gufi,
                aircraft_id,
                flight_reference=flight_ref,
                departure_airport=flight_plan_data.get("departure_airport"),
                arrival_airport=flight_plan_data.get("arrival_airport"),
                scheduled_departure=igtd,
                current_status="PLANNED",
            )

            # Prefer row by canonical GUFI (exact, then case-insensitive), then by flight_reference.
            # Avoids ix_flight_plan_gufi violations when two rows differ only by GUFI casing.
            existing_id = None
            if gufi:
                existing_id = session.execute(
                    text("SELECT id FROM flight_plan WHERE gufi = :gufi LIMIT 1"),
                    {"gufi": gufi},
                ).scalar()
            if not existing_id and gufi:
                existing_id = session.execute(
                    text(
                        """
                        SELECT id FROM flight_plan
                        WHERE gufi IS NOT NULL
                          AND UPPER(TRIM(gufi)) = :gufi_norm
                        LIMIT 1
                        """
                    ),
                    {"gufi_norm": gufi.upper()},
                ).scalar()
            if not existing_id and flight_ref:
                existing_id = session.execute(
                    text(
                        """
                        SELECT id FROM flight_plan
                        WHERE aircraft_id = :aircraft_id
                          AND flight_reference = :flight_ref
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"aircraft_id": aircraft_id, "flight_ref": flight_ref},
                ).scalar()

            if existing_id:
                # Update existing flight plan (preserve igtd/route when message omits them)
                upd_params = {
                    "existing_id": existing_id,
                    "aircraft_id": aircraft_id,
                    "gufi": gufi,
                    "flight_ref": flight_ref,
                    "dep_apt": flight_plan_data.get("departure_airport"),
                    "arr_apt": flight_plan_data.get("arrival_airport"),
                    "igtd": igtd,
                    "route": flight_plan_data.get("route_text"),
                }
                try:
                    with session.begin_nested():
                        session.execute(
                            text(
                                f"""
                                UPDATE flight_plan
                                SET aircraft_id = :aircraft_id,
                                    gufi = :gufi,
                                    flight_reference = :flight_ref,
                                    departure_airport = :dep_apt,
                                    arrival_airport = :arr_apt,
                                    igtd = COALESCE(:igtd, igtd),
                                    {FP_ROUTE_COL} = COALESCE(:route, {FP_ROUTE_COL}),
                                    {FP_FLIGHT_ID_COL} = :aircraft_id
                                WHERE id = :existing_id
                                """
                            ),
                            upd_params,
                        )
                except IntegrityError as e:
                    orig = getattr(e, "orig", None)
                    pgcode = getattr(orig, "pgcode", None) if orig else None
                    if pgcode == "23505":
                        logger.warning(
                            "flight_plan UPDATE gufi conflict (23505); "
                            "retrying without changing gufi for id={}: {}",
                            existing_id,
                            e,
                        )
                        with session.begin_nested():
                            session.execute(
                                text(
                                    f"""
                                    UPDATE flight_plan
                                    SET aircraft_id = :aircraft_id,
                                        flight_reference = :flight_ref,
                                        departure_airport = :dep_apt,
                                        arrival_airport = :arr_apt,
                                        igtd = COALESCE(:igtd, igtd),
                                        {FP_ROUTE_COL} = COALESCE(:route, {FP_ROUTE_COL}),
                                        {FP_FLIGHT_ID_COL} = :aircraft_id
                                    WHERE id = :existing_id
                                    """
                                ),
                                upd_params,
                            )
                    else:
                        raise
            else:
                # Insert new flight plan
                # Generate a unique flight_plan_id (using aircraft_id + flight_ref + timestamp)
                import hashlib

                timestamp_str = datetime.utcnow().isoformat()
                plan_id_input = (
                    f"{aircraft_id}_{flight_ref}_{timestamp_str}"
                    if flight_ref
                    else f"{aircraft_id}_{timestamp_str}"
                )
                flight_plan_id = hashlib.md5(plan_id_input.encode()).hexdigest()[:16]

                # Check if this flight_plan_id already exists (unlikely but possible)
                check_result = session.execute(
                    text(
                        "SELECT id FROM flight_plan WHERE flight_plan_id = :plan_id LIMIT 1"
                    ),
                    {"plan_id": flight_plan_id},
                )
                if check_result.scalar():
                    # If collision, append timestamp
                    flight_plan_id = (
                        f"{flight_plan_id}_{int(datetime.utcnow().timestamp())}"
                    )

                try:
                    with session.begin_nested():
                        session.execute(
                            text(
                                f"""
                            INSERT INTO flight_plan
                            (aircraft_id, gufi, flight_reference, departure_airport, arrival_airport,
                             igtd, {FP_ROUTE_COL}, flight_plan_id, {FP_FLIGHT_ID_COL})
                            VALUES (:aircraft_id, :gufi, :flight_ref, :dep_apt, :arr_apt, :igtd, :route, :flight_plan_id, :aircraft_id)
                        """
                            ),
                            {
                                "aircraft_id": aircraft_id,
                                "gufi": gufi,
                                "flight_ref": flight_ref,
                                "dep_apt": flight_plan_data.get("departure_airport"),
                                "arr_apt": flight_plan_data.get("arrival_airport"),
                                "igtd": igtd,
                                "route": flight_plan_data.get("route_text"),
                                "flight_plan_id": flight_plan_id,
                            },
                        )
                except IntegrityError as e:
                    orig = getattr(e, "orig", None)
                    pgcode = getattr(orig, "pgcode", None) if orig else None
                    if pgcode == "23505":
                        logger.warning(
                            "flight_plan INSERT unique violation (23505); attempting update: {}",
                            e,
                        )
                        if gufi:
                            result = session.execute(
                                text(
                                    "SELECT id FROM flight_plan WHERE gufi = :gufi LIMIT 1"
                                ),
                                {"gufi": gufi},
                            )
                            existing_id = result.scalar()
                            if existing_id:
                                session.execute(
                                    text(
                                        f"""
                                        UPDATE flight_plan
                                        SET aircraft_id = :aircraft_id,
                                            flight_reference = :flight_ref,
                                            departure_airport = :dep_apt,
                                            arrival_airport = :arr_apt,
                                            igtd = COALESCE(:igtd, igtd),
                                            {FP_ROUTE_COL} = COALESCE(:route, {FP_ROUTE_COL}),
                                            {FP_FLIGHT_ID_COL} = :aircraft_id
                                        WHERE id = :existing_id
                                    """
                                    ),
                                    {
                                        "existing_id": existing_id,
                                        "aircraft_id": aircraft_id,
                                        "flight_ref": flight_ref,
                                        "dep_apt": flight_plan_data.get(
                                            "departure_airport"
                                        ),
                                        "arr_apt": flight_plan_data.get(
                                            "arrival_airport"
                                        ),
                                        "igtd": igtd,
                                        "route": flight_plan_data.get("route_text"),
                                    },
                                )
                    else:
                        raise

            try:
                auto_resolve_gufi_on_flight_plan_store(
                    aircraft_id, gufi, session=session
                )
            except Exception as e:
                logger.warning(f"Error auto-resolving GUFI: {e}")

            logger.debug(f"Stored flight plan for aircraft {aircraft_id}, GUFI {gufi}")

        session.commit()
        logger.info(f"Successfully stored {len(flight_plan_data_list)} flight plans")

    except SQLAlchemyError as e:
        logger.error("SQLAlchemyError storing flight plans: {}", str(e), exc_info=True)
        session.rollback()
        raise
    except Exception as e:
        logger.error("Error storing flight plans: {}", str(e), exc_info=True)
        session.rollback()
        raise
    finally:
        if created_locally:
            session.close()
