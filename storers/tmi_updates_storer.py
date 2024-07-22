from sqlalchemy.orm import Session
from models.sqlalchemy.tmi_updates import TmiUpdatesDBModel
from db_config import SessionLocal
from utils.logger import main_logger as logger


def store_tmi_flight_list(parsed_data):
    """
    store_tmi_flight_list _summary_

    Args:
        parsed_data (_type_): _description_
    """
    try:
        with SessionLocal() as session:
            for flight in parsed_data:
                aircraft = (
                    session.query(TmiUpdatesDBModel)
                    .filter_by(aircraft_id=flight.flight.aircraftId)
                    .first()
                )
                if not aircraft:
                    aircraft = TmiUpdatesDBModel(
                        aircraft_id=flight.flight.aircraftId,
                        gufi=flight.flight.gufi,
                        flight_reference=flight.flightReference,
                        status=flight.status,
                    )
                    session.add(aircraft)

                tmi_update = TmiUpdatesDBModel(
                    aircraft_id=flight.flight.aircraftId,
                    update_time=flight.tmiFlightInfoList.tmi.lastUpdateTime,
                    update_type=flight.tmiFlightInfoList.tmi.updateType,
                    last_update_time=flight.tmiFlightInfoList.tmi.lastUpdateTime,
                    fca_id=flight.tmiFlightInfoList.tmi.fcaId,
                )
                session.add(tmi_update)

            session.commit()
            logger.info("Successfully stored TMI flight list data.")
    except Exception as e:
        logger.error(f"Error storing TMI flight list data: {e}", exc_info=True)
