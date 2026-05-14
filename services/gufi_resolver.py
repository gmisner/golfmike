"""
GUFI Resolution Service
Updates temporary GUFIs with real ones when flight plans arrive
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from db_config import SessionLocal
from storers.flight_hub import normalize_plan_gufi
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger
from typing import Optional, Dict, Any


def resolve_gufi_for_aircraft(
    aircraft_id: str, session: Session = None
) -> Optional[str]:
    """
    Resolve GUFI for an aircraft by looking up in flight_plan table

    Args:
        aircraft_id: Aircraft identifier
        session: Database session

    Returns:
        GUFI if found, None otherwise
    """
    aircraft_id = normalize_aircraft_id(aircraft_id)
    if not aircraft_id:
        return None

    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True

    try:
        # Look up GUFI from flight_plan table
        result = session.execute(
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
        )

        row = result.fetchone()
        gufi = row[0] if row else None

        if gufi:
            logger.debug(f"Resolved GUFI {gufi} for aircraft {aircraft_id}")

        return gufi

    except Exception as e:
        logger.error("Error resolving GUFI: {}", str(e), exc_info=True)
        raise
    finally:
        if created_locally:
            session.close()


def update_temporary_gufis(
    session: Session = None, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Update temporary GUFIs (starting with TEMP_) with real GUFIs from flight_plan

    Args:
        session: Database session
        dry_run: If True, only report what would be updated without making changes

    Returns:
        Dictionary with update statistics
    """
    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True

    stats = {
        "flights_updated": 0,
        "route_assignments_updated": 0,
        "track_updates_updated": 0,
        "alerts_updated": 0,
        "updates": [],
    }

    try:
        # Find all flights with temporary GUFIs
        result = session.execute(
            text(
                """
                SELECT f.gufi, f.aircraft_id
                FROM flights f
                WHERE f.gufi LIKE 'TEMP_%'
            """
            )
        )

        temp_flights = result.fetchall()

        for temp_gufi, aircraft_id in temp_flights:
            # Try to find real GUFI
            real_gufi = resolve_gufi_for_aircraft(aircraft_id, session=session)

            if not real_gufi:
                continue

            # Check if real GUFI already exists in flights table
            check_result = session.execute(
                text("SELECT COUNT(*) FROM flights WHERE gufi = :gufi"),
                {"gufi": real_gufi},
            )
            real_exists = check_result.scalar() > 0

            if not dry_run:
                if real_exists:
                    # Merge: Update all references from temp to real, then delete temp
                    logger.info(
                        f"Merging temp GUFI {temp_gufi} into existing {real_gufi} for aircraft {aircraft_id}"
                    )

                    # Update route_assignments
                    route_result = session.execute(
                        text(
                            """
                            UPDATE route_assignments
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["route_assignments_updated"] += route_result.rowcount

                    # Update track_updates
                    track_result = session.execute(
                        text(
                            """
                            UPDATE track_updates
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["track_updates_updated"] += track_result.rowcount

                    # Update flight_alerts
                    alert_result = session.execute(
                        text(
                            """
                            UPDATE flight_alerts
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["alerts_updated"] += alert_result.rowcount

                    # Delete temp flight record
                    session.execute(
                        text("DELETE FROM flights WHERE gufi = :temp_gufi"),
                        {"temp_gufi": temp_gufi},
                    )

                else:
                    # Simple update: just change the GUFI
                    logger.info(
                        f"Updating temp GUFI {temp_gufi} to {real_gufi} for aircraft {aircraft_id}"
                    )

                    # Update flights
                    session.execute(
                        text(
                            """
                            UPDATE flights
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )

                    # Update route_assignments
                    route_result = session.execute(
                        text(
                            """
                            UPDATE route_assignments
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["route_assignments_updated"] += route_result.rowcount

                    # Update track_updates
                    track_result = session.execute(
                        text(
                            """
                            UPDATE track_updates
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["track_updates_updated"] += track_result.rowcount

                    # Update flight_alerts
                    alert_result = session.execute(
                        text(
                            """
                            UPDATE flight_alerts
                            SET gufi = :real_gufi
                            WHERE gufi = :temp_gufi
                        """
                        ),
                        {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
                    )
                    stats["alerts_updated"] += alert_result.rowcount

                stats["flights_updated"] += 1
                stats["updates"].append(
                    {
                        "temp_gufi": temp_gufi,
                        "real_gufi": real_gufi,
                        "aircraft_id": aircraft_id,
                        "merged": real_exists,
                    }
                )
            else:
                # Dry run - just report
                stats["updates"].append(
                    {
                        "temp_gufi": temp_gufi,
                        "real_gufi": real_gufi,
                        "aircraft_id": aircraft_id,
                        "merged": real_exists,
                    }
                )

        if not dry_run:
            session.commit()
            logger.info(f"Updated {stats['flights_updated']} temporary GUFIs")

        return stats

    except Exception as e:
        logger.error("Error updating temporary GUFIs: {}", str(e), exc_info=True)
        if not dry_run:
            session.rollback()
        raise
    finally:
        if created_locally:
            session.close()


def auto_resolve_gufi_on_flight_plan_store(
    aircraft_id: str, gufi: str, session: Session = None
) -> None:
    """
    Automatically resolve temporary GUFIs when a flight plan is stored

    Args:
        aircraft_id: Aircraft identifier
        gufi: GUFI from flight plan
        session: Database session
    """
    aircraft_id = normalize_aircraft_id(aircraft_id)
    if not aircraft_id:
        return

    created_locally = False
    if session is None:
        session = SessionLocal()
        created_locally = True

    try:
        # Check if there are any temporary GUFIs for this aircraft
        result = session.execute(
            text(
                """
                SELECT gufi FROM flights
                WHERE aircraft_id = :aircraft_id
                AND gufi LIKE 'TEMP_%'
            """
            ),
            {"aircraft_id": aircraft_id},
        )

        temp_gufis = [row[0] for row in result.fetchall()]

        if not temp_gufis:
            return

        real_gufi = normalize_plan_gufi(gufi)
        if not real_gufi:
            return

        merged = 0
        for temp_gufi in temp_gufis:
            temp_norm = normalize_plan_gufi(temp_gufi)
            # Current flight plan still uses this temp; flight_plan FK blocks DELETE — skip
            if temp_norm == real_gufi:
                logger.debug(
                    "Skip auto-resolve for {}: still canonical GUFI for {}",
                    temp_gufi,
                    aircraft_id,
                )
                continue

            logger.info(
                "Auto-resolving temp GUFI {} to {} for aircraft {}",
                temp_gufi,
                real_gufi,
                aircraft_id,
            )

            # Repoint flight_plan before deleting the temp flights row (flight_plan_gufi_fkey)
            session.execute(
                text(
                    "UPDATE flight_plan SET gufi = :real_gufi WHERE gufi = :temp_gufi"
                ),
                {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
            )

            session.execute(
                text(
                    "UPDATE route_assignments SET gufi = :real_gufi WHERE gufi = :temp_gufi"
                ),
                {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
            )

            session.execute(
                text(
                    "UPDATE track_updates SET gufi = :real_gufi WHERE gufi = :temp_gufi"
                ),
                {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
            )

            session.execute(
                text(
                    "UPDATE flight_alerts SET gufi = :real_gufi WHERE gufi = :temp_gufi"
                ),
                {"real_gufi": real_gufi, "temp_gufi": temp_gufi},
            )

            session.execute(
                text("DELETE FROM flights WHERE gufi = :temp_gufi"),
                {"temp_gufi": temp_gufi},
            )
            merged += 1

        if merged == 0:
            return

        session.commit()
        logger.info(
            "Auto-resolved {} temporary GUFI(s) for aircraft {}",
            merged,
            aircraft_id,
        )

    except Exception as e:
        logger.error("Error auto-resolving GUFI: {}", str(e), exc_info=True)
        if not created_locally:
            session.rollback()
        raise
    finally:
        if created_locally:
            session.close()
