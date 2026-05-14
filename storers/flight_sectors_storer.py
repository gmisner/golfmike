from typing import List, Optional

from sqlalchemy.orm import Session

from db_config import SessionLocal
from models.pydantic.flight_sectors import FlightSectorsModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_sectors import FlightSectorsDBModel
from utils.logger import main_logger as logger


def store_flight_sectors(
    assignments: List[FlightSectorsModel], session: Optional[Session] = None
) -> None:
    """Persist flight sector assignments. Pass ``session`` when called from ``parse_and_store_to_database``."""
    created_locally = session is None
    if session is None:
        session = SessionLocal()
    elif not isinstance(session, Session):
        logger.error(
            "Invalid session type: {}. Expected SQLAlchemy Session.",
            type(session),
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    try:
        new_aircrafts = []
        new_assignments = []

        for assignment in assignments:
            logger.debug(
                "Processing assignment for aircraft ID: {}",
                assignment.aircraftId,
            )

            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=assignment.aircraftId)
                .first()
            )
            if not aircraft:
                logger.debug(
                    "Creating new aircraft with ID: {}",
                    assignment.aircraftId,
                )
                aircraft = AircraftDBModel(aircraft_id=assignment.aircraftId)
                new_aircrafts.append(aircraft)

            airspace_assignment = FlightSectorsDBModel(
                aircraft_id=assignment.aircraftId,
                flight_ref=assignment.flightRef,
                dep_arpt=assignment.depArpt,
                arr_arpt=assignment.arrArpt,
                igtd=assignment.igtd,
                fixes=assignment.fixes,
                waypoints=assignment.waypoints,
                sectors=assignment.sectors,
                airways=assignment.airways,
                centers=assignment.centers,
            )
            new_assignments.append(airspace_assignment)

        if new_aircrafts:
            logger.debug("Adding {} new aircraft records", len(new_aircrafts))
            session.bulk_save_objects(new_aircrafts)

        if new_assignments:
            logger.debug(
                "Adding {} new flight sector assignment records",
                len(new_assignments),
            )
            session.bulk_save_objects(new_assignments)

        if created_locally:
            session.commit()
        logger.info("Flight sectors stored successfully.")

    except Exception as e:
        logger.error("Error storing flight sectors: {}", e, exc_info=True)
        if created_locally:
            session.rollback()
        raise
    finally:
        if created_locally:
            session.close()
