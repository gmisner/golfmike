# storers/tmi_flight_list_storer.py
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


def store_tmi_flight_list(parsed_data, batch_size=100):
    session = SessionLocal()
    try:
        new_aircrafts = []
        new_flight_plans = []
        new_fxa_flights = []

        for flight in parsed_data:
            try:
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
                    aircraft = AircraftDBModel(aircraft_id=aircraft_id)
                    new_aircrafts.append(aircraft)
                    logger.debug(f"Prepared to create aircraft with ID {aircraft_id}")

                # Check if flight plan already exists
                flight_plan = (
                    session.query(FlightPlanDBModel)
                    .filter_by(flight_plan_id=gufi)
                    .first()
                )
                if flight_plan:
                    logger.debug(
                        f"Flight plan with ID {gufi} already exists. Updating existing flight plan."
                    )
                    flight_plan.igtd = igtd
                    flight_plan.departure_airport = departure_airport
                    flight_plan.arrival_airport = arrival_airport
                else:
                    # Create new flight plan
                    flight_plan = FlightPlanDBModel(
                        flight_plan_id=gufi,
                        gufi=gufi,
                        aircraft_id=aircraft_id,
                        igtd=igtd,
                        departure_airport=departure_airport,
                        arrival_airport=arrival_airport,
                    )
                    new_flight_plans.append(flight_plan)
                    logger.debug(
                        f"Prepared to create flight plan for aircraft ID {aircraft_id} with flight_plan_id {gufi}"
                    )

                # Verify flight plan creation
                if not flight_plan or not flight_plan.flight_plan_id:
                    logger.error(
                        f"Flight plan for aircraft ID {aircraft_id} was not created successfully. Skipping FXA flights."
                    )
                    continue

                # Add FXA flight records
                for fxa_flight in flight["fxa_flights"]:
                    fxa_flight_model = FxaFlightDBModel(
                        fxa_id=fxa_flight["fxaId"],
                        fca_id=fxa_flight.get("fcaId"),
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
                        flight_plan_id=flight_plan.flight_plan_id,
                        aircraft_id=aircraft_id,
                    )
                    new_fxa_flights.append(fxa_flight_model)

                # Commit batches
                if (
                    len(new_aircrafts) >= batch_size
                    or len(new_flight_plans) >= batch_size
                    or len(new_fxa_flights) >= batch_size
                ):
                    session.bulk_save_objects(new_aircrafts)
                    session.bulk_save_objects(new_flight_plans)
                    session.bulk_save_objects(new_fxa_flights)
                    session.commit()
                    logger.debug(
                        f"Committed batch of {len(new_aircrafts)} aircraft, {len(new_flight_plans)} flight plans, and {len(new_fxa_flights)} FXA flights"
                    )

                    # Clear the lists after commit
                    new_aircrafts.clear()
                    new_flight_plans.clear()
                    new_fxa_flights.clear()

            except (IntegrityError, SQLAlchemyError) as e:
                session.rollback()
                logger.error(
                    f"Error processing flight data: {flight['aircraft_id']}, Error: {e}",
                    exc_info=True,
                )

        # Commit any remaining records in the batch
        if new_aircrafts or new_flight_plans or new_fxa_flights:
            session.bulk_save_objects(new_aircrafts)
            session.bulk_save_objects(new_flight_plans)
            session.bulk_save_objects(new_fxa_flights)
            session.commit()
            logger.debug(
                f"Committed final batch of {len(new_aircrafts)} aircraft, {len(new_flight_plans)} flight plans, and {len(new_fxa_flights)} FXA flights"
            )

        logger.success("All TMI flight list data stored successfully")

    except Exception as e:
        session.rollback()
        logger.error(f"Error storing TMI flight list: {e}", exc_info=True)
    finally:
        session.close()
