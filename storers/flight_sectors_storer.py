from db_config import SessionLocal
from typing import List
from models.pydantic.flight_sectors import FlightSectorsModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_sectors import FlightSectorsDBModel
from utils.logger import main_logger as logger


def store_flight_sectors(assignments: List[FlightSectorsModel]):
    try:
        with SessionLocal() as session:
            new_aircrafts = []
            new_assignments = []

            for assignment in assignments:
                logger.debug(
                    f"Processing assignment for aircraft ID: {assignment.aircraftId}"
                )

                # Fetch or create aircraft
                aircraft = (
                    session.query(AircraftDBModel)
                    .filter_by(aircraft_id=assignment.aircraftId)
                    .first()
                )
                if not aircraft:
                    logger.debug(
                        f"Creating new aircraft with ID: {assignment.aircraftId}"
                    )
                    aircraft = AircraftDBModel(aircraft_id=assignment.aircraftId)
                    new_aircrafts.append(aircraft)

                # Prepare flight sector assignment
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

            # Bulk insert new aircraft and assignments
            if new_aircrafts:
                logger.debug(f"Adding {len(new_aircrafts)} new aircraft records")
                session.bulk_save_objects(new_aircrafts)

            if new_assignments:
                logger.debug(
                    f"Adding {len(new_assignments)} new flight sector assignment records"
                )
                session.bulk_save_objects(new_assignments)

            # Commit all changes
            session.commit()
            logger.info("Flight sectors stored successfully.")

    except Exception as e:
        logger.error(f"Error storing flight sectors: {e}", exc_info=True)
        raise e  # Reraise the exception to handle it further up if needed
