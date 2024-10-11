from db_config import SessionLocal
from models.sqlalchemy import AircraftDBModel, FlightPlanDBModel
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError


def store_tmi_flight_list(parsed_data):
    try:
        with SessionLocal() as session:
            for flight in parsed_data:
                try:
                    logger.debug(f"Processing flight: {flight}")

                    # Fetch or create aircraft
                    aircraft_id = flight["aircraft_id"]
                    aircraft = (
                        session.query(AircraftDBModel)
                        .filter_by(aircraft_id=aircraft_id)
                        .first()
                    )
                    if not aircraft:
                        aircraft = AircraftDBModel(aircraft_id=aircraft_id)
                        session.add(aircraft)
                        session.commit()  # Commit each new aircraft to avoid foreign key issues

                    # Create or update flight plan
                    gufi = flight["gufi"]
                    flight_plan = (
                        session.query(FlightPlanDBModel)
                        .filter_by(flight_plan_id=gufi)
                        .first()
                    )
                    if flight_plan:
                        logger.debug(f"Updating flight plan {gufi}")
                        flight_plan.igtd = flight["igtd"]
                        flight_plan.departure_airport = flight["departure_airport"]
                        flight_plan.arrival_airport = flight["arrival_airport"]
                    else:
                        logger.debug(f"Creating new flight plan {gufi}")
                        flight_plan = FlightPlanDBModel(
                            flight_plan_id=gufi,
                            gufi=gufi,
                            aircraft_id=aircraft_id,
                            igtd=flight["igtd"],
                            departure_airport=flight["departure_airport"],
                            arrival_airport=flight["arrival_airport"],
                        )
                        session.add(flight_plan)

                    # Commit after each addition/update
                    session.commit()
                    logger.debug(f"Successfully committed flight plan {gufi}")

                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(
                        f"Error processing flight {flight}: {e}", exc_info=True
                    )

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
