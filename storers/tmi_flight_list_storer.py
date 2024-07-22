from sqlalchemy.orm import Session
from models.sqlalchemy import AircraftDBModel, FlightPlanDBModel, FxaUpdatesDBModel
from utils.logger import main_logger as logger


def store_tmi_flight_list(session: Session, tmi_flight_list_model):
    try:
        for flight_data in tmi_flight_list_model.flight:
            try:
                aircraft = session.query(AircraftDBModel).filter_by(aircraft_id=flight_data.aircraftId).first()
                if not aircraft:
                    logger.debug(f"Creating new aircraft with ID {flight_data.aircraftId}")
                    aircraft = AircraftDBModel(aircraft_id=flight_data.aircraftId)
                    session.add(aircraft)
                    session.commit()
                    logger.debug(f"Aircraft with ID {flight_data.aircraftId} created")
                
                session.expire_all()
                aircraft = session.query(AircraftDBModel).filter_by(aircraft_id=flight_data.aircraftId).first()
                logger.debug(f"Aircraft fetched with ID {aircraft.aircraft_id}")

                flight_plan = session.query(FlightPlanDBModel).filter_by(flight_plan_id=flight_data.gufi).first()
                if not flight_plan:
                    logger.debug(f"Creating new flight plan with GUFI {flight_data.gufi}")
                    flight_plan = FlightPlanDBModel(
                        flight_plan_id=flight_data.gufi,
                        aircraft_id=aircraft.aircraft_id,
                        departure_point=flight_data.departurePoint,
                        arrival_point=flight_data.arrivalPoint,
                        flight_reference=flight_data.flightReference,
                    )
                    session.add(flight_plan)
                    session.commit()
                    logger.debug(f"Flight plan with GUFI {flight_data.gufi} created")

                for fxa_flight in tmi_flight_list_model.tmiFlightInfoList.fxaFlightData.fxaFlight:
                    fxa_update = FxaUpdatesDBModel(
                        aircraft_id=aircraft.aircraft_id,
                        flight_plan_id=flight_plan.flight_plan_id,
                        fca_id=fxa_flight.fcaId,
                        fca_name=fxa_flight.fcaName,
                        last_update=fxa_flight.lastUpdate,
                        bentry_tm=fxa_flight.bentryTm,
                        create_tm=fxa_flight.createTm,
                        eentry_tm=fxa_flight.eentryTm,
                        entry_tm=fxa_flight.entryTm,
                        exit_tm=fxa_flight.exitTm,
                        extended_exit_tm=fxa_flight.extendedExitTm,
                        ientry_tm=fxa_flight.ientryTm,
                        oentry_tm=fxa_flight.oentryTm,
                        entry_lat=fxa_flight.entryLat,
                        entry_lon=fxa_flight.entryLon,
                        entry_heading=fxa_flight.entryHeading,
                        exit_ind=fxa_flight.exitInd,
                    )
                    session.add(fxa_update)
                    session.commit()
                    logger.debug(f"FXA update added for flight plan {flight_data.gufi}")

            except Exception as inner_e:
                logger.error(f"Error processing flight data {flight_data.gufi}: {inner_e}", exc_info=True)

        logger.info("TMI flight list data stored successfully.")
    except Exception as e:
        logger.error(f"Error storing TMI flight list data: {e}", exc_info=True)
        raise
