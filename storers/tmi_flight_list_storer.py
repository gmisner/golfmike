from db_config import SessionLocal
from models.sqlalchemy import AircraftDBModel, FlightPlanDBModel
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def store_tmi_flight_list(parsed_data, session=None):
    logger.debug("Starting store_tmi_flight_list function")

    created_locally = session is None

    # Verify session type and create a new session if none is provided
    if session is None:
        logger.debug("No session provided, creating a new session")
        session = SessionLocal()
    elif not isinstance(session, Session):
        logger.error(
            f"Invalid session type: {type(session)}. Expected <class 'sqlalchemy.orm.session.Session'>."
        )
        raise TypeError("Invalid session type. Expected SQLAlchemy Session.")

    logger.debug(
        f"Session type after check: {type(session)}"
    )  # Verify correct session type

    try:
        # Ensure session is correctly bound
        if not session.bind:
            logger.error("Session is not bound to any engine.")
            raise RuntimeError("Session is not bound to any engine.")

        for index, flight in enumerate(parsed_data):
            # Process each flight entry
            aircraft_id = flight.get("aircraft_id")
            gufi = flight.get("gufi")
            igtd = flight.get("igtd")
            departure_airport = flight.get("departure_airport")
            arrival_airport = flight.get("arrival_airport")

            if not all([aircraft_id, gufi, igtd, departure_airport, arrival_airport]):
                logger.error(f"Missing required data in flight: {flight}")
                continue  # Skip incomplete entries

            logger.debug(f"Processing flight {index + 1}/{len(parsed_data)}: {flight}")

            # Fetch or create AircraftDBModel entry
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=aircraft_id)
                .first()
            )
            if aircraft is None:
                aircraft = AircraftDBModel(aircraft_id=aircraft_id)
                session.add(aircraft)
                logger.debug(f"Added aircraft {aircraft_id}")

            # Fetch or create FlightPlanDBModel entry
            flight_plan = (
                session.query(FlightPlanDBModel).filter_by(flight_plan_id=gufi).first()
            )
            if not flight_plan:
                flight_plan = FlightPlanDBModel(
                    flight_plan_id=gufi,
                    gufi=gufi,
                    aircraft_id=aircraft_id,
                    igtd=igtd,
                    departure_airport=departure_airport,
                    arrival_airport=arrival_airport,
                )
                session.add(flight_plan)
                logger.debug(f"Added new flight plan for {gufi}")
            else:
                flight_plan.igtd = igtd
                flight_plan.departure_airport = departure_airport
                flight_plan.arrival_airport = arrival_airport

            # Commit changes every 100 flights or at the end
            if (index + 1) % 100 == 0 or index == len(parsed_data) - 1:
                session.commit()
                logger.debug(f"Commit successful after processing {index + 1} flights.")

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError occurred while processing flight {flight}: {e}")
        session.rollback()

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if session:
            session.rollback()

    finally:
        if created_locally and session:
            SessionLocal.remove()
            logger.debug("Scoped session removed.")

    logger.debug("Finished store_tmi_flight_list function")
