from db_config import SessionLocal
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.sqlalchemy import (
    TmiUpdatesDBModel,
    FxaFlightDBModel,
    AircraftDBModel,
    FlightPlanDBModel,
)
from utils.logger import main_logger as logger
import time


def store_tmi_flight_list(session: SessionLocal, parsed_data, batch_size: int = 100):
    try:
        # Caches for batch processing
        new_aircrafts = []
        new_flight_plans = []
        new_fxa_flights = []

        for flight in parsed_data:
            aircraft_id = flight["aircraft_id"]
            gufi = flight["gufi"]
            igtd = flight["igtd"]
            departure_airport = flight["departure_airport"]
            arrival_airport = flight["arrival_airport"]

            # Fetch or create aircraft
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=aircraft_id)
                .first()
            )
            if not aircraft:
                try:
                    aircraft = AircraftDBModel(aircraft_id=aircraft_id)
                    new_aircrafts.append(aircraft)
                    logger.info(f"Prepared to create aircraft with ID {aircraft_id}")
                except IntegrityError as e:
                    logger.error(
                        f"Error creating aircraft with ID {aircraft_id}: {str(e)}"
                    )
                    continue  # Skip to the next flight if aircraft creation fails

            # Check if flight plan already exists
            flight_plan = (
                session.query(FlightPlanDBModel).filter_by(flight_plan_id=gufi).first()
            )
            if flight_plan:
                logger.info(
                    f"Flight plan with ID {gufi} already exists. Updating existing flight plan."
                )
                flight_plan.igtd = igtd
                flight_plan.departure_airport = departure_airport
                flight_plan.arrival_airport = arrival_airport
                session.commit()
            else:
                # Create new flight plan
                try:
                    flight_plan = FlightPlanDBModel(
                        flight_plan_id=gufi,  # Use gufi as flight_plan_id
                        gufi=gufi,
                        aircraft_id=aircraft_id,
                        igtd=igtd,
                        departure_airport=departure_airport,
                        arrival_airport=arrival_airport,
                    )
                    new_flight_plans.append(flight_plan)
                    logger.info(
                        f"Prepared to create flight plan for aircraft ID {aircraft_id} with flight_plan_id {gufi}"
                    )
                except IntegrityError as e:
                    logger.info(
                        f"Error creating flight plan for aircraft ID {aircraft_id}: {str(e)}"
                    )
                    continue  # Skip to the next flight if flight plan creation fails

            # Verify flight plan creation
            if not flight_plan or not flight_plan.flight_plan_id:
                logger.error(
                    f"Flight plan for aircraft ID {aircraft_id} was not created successfully. Skipping FXA flights."
                )
                continue

            # Add FXA flight entries
            for fxa_flight in flight["fxa_flights"]:
                try:
                    fxa_flight_model = FxaFlightDBModel(
                        fxa_id=fxa_flight["fxaId"],
                        fca_id=fxa_flight.get("fcaId"),  # Use .get() to avoid KeyError
                        fca_name=fxa_flight["fcaName"],
                        last_update=fxa_flight["lastUpdate"],
                        bentry_tm=fxa_flight["bentryTm"],
                        create_tm=fxa_flight["createTm"],
                        eentry_tm=fxa_flight["eentryTm"],
                        entry_tm=fxa_flight["entryTm"],
                        exit_tm=fxa_flight["exitTm"],
                        extended_exit_tm=fxa_flight["extendedExitTm"],
                        ientry_tm=fxa_flight["ientryTm"],
                        oentry_tm=fxa_flight["oentryTm"],
                        entry_lat=fxa_flight["entryLat"],
                        entry_lon=fxa_flight["entryLon"],
                        entry_heading=fxa_flight["entryHeading"],
                        exit_ind=fxa_flight["exitInd"],
                        flight_plan_id=flight_plan.flight_plan_id,  # Use the correct flight_plan_id
                        aircraft_id=aircraft_id,
                    )
                    new_fxa_flights.append(fxa_flight_model)
                    logger.info(
                        f"Prepared to create FXA flight for aircraft ID {aircraft_id}"
                    )

                    if len(new_fxa_flights) >= batch_size:
                        # Bulk insert FXA flights
                        session.bulk_save_objects(new_fxa_flights)
                        session.commit()
                        logger.debug(
                            f"Committed batch of {len(new_fxa_flights)} FXA flights"
                        )
                        new_fxa_flights.clear()

                except IntegrityError as e:
                    session.rollback()
                    logger.error(
                        f"Error creating FXA flight for aircraft ID {aircraft_id}: {str(e)}"
                    )
                    continue  # Skip to the next FXA flight if insertion fails

            # Commit in batches
            if len(new_aircrafts) >= batch_size or len(new_flight_plans) >= batch_size:
                if new_aircrafts:
                    session.bulk_save_objects(new_aircrafts)
                    logger.debug(f"Committed batch of {len(new_aircrafts)} aircraft")
                    new_aircrafts.clear()
                if new_flight_plans:
                    session.bulk_save_objects(new_flight_plans)
                    logger.debug(
                        f"Committed batch of {len(new_flight_plans)} flight plans"
                    )
                    new_flight_plans.clear()
                session.commit()

        # Commit any remaining records in the batch
        if new_aircrafts or new_flight_plans or new_fxa_flights:
            if new_aircrafts:
                session.bulk_save_objects(new_aircrafts)
                logger.debug(f"Committed final batch of {len(new_aircrafts)} aircraft")
            if new_flight_plans:
                session.bulk_save_objects(new_flight_plans)
                logger.debug(
                    f"Committed final batch of {len(new_flight_plans)} flight plans"
                )
            if new_fxa_flights:
                session.bulk_save_objects(new_fxa_flights)
                logger.debug(
                    f"Committed final batch of {len(new_fxa_flights)} FXA flights"
                )
            session.commit()

        logger.success("TMI flight list data stored successfully.")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error storing TMI flight list data: {e}", exc_info=True)
    finally:
        session.close()
