from db_config import SessionLocal
from typing import List
from models.pydantic.flight_sectors import FlightSectorsModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.sqlalchemy.flight_sectors import FlightSectorsDBModel


def store_flight_sectors(assignments: List[FlightSectorsModel]):
    session = SessionLocal()
    try:
        for assignment in assignments:
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=assignment.aircraftId)
                .first()
            )
            if not aircraft:
                aircraft = AircraftDBModel(aircraft_id=assignment.aircraftId)
                session.add(aircraft)
                session.commit()

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
            session.add(airspace_assignment)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
