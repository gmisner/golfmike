# storers/tmi_flight_list_storer.py

from sqlalchemy.orm import Session
from models.sqlalchemy.tmi_updates import TmiUpdatesDBModel
from models.sqlalchemy.fxa_updates import FxaUpdatesDBModel
from models.sqlalchemy.aircraft import AircraftDBModel
from models.pydantic.tmi_flight_list import TmiFlightListModel
from db_config import SessionLocal
from utils.logger import main_logger as logger


def store_tmi_flight_list(tmi_flight_list: TmiFlightListModel):
    try:
        with SessionLocal() as session:
            aircraft = (
                session.query(AircraftDBModel)
                .filter_by(aircraft_id=tmi_flight_list.flight)
                .first()
            )
            if not aircraft:
                aircraft = AircraftDBModel(
                    aircraft_id=tmi_flight_list.flight,
                    gufi=tmi_flight_list.flightReference,
                )
                session.add(aircraft)

            tmi_update = TmiUpdatesDBModel(
                aircraft_id=tmi_flight_list.flight,
                update_time=tmi_flight_list.tmiFlightInfoList.tmi.lastUpdateTime,
                update_type=tmi_flight_list.tmiFlightInfoList.tmi.updateType,
                last_update_time=tmi_flight_list.tmiFlightInfoList.tmi.lastUpdateTime,
                fca_id=tmi_flight_list.tmiFlightInfoList.tmi.fcaId,
            )
            session.add(tmi_update)

            for fxa_flight in tmi_flight_list.tmiFlightInfoList.fxaFlightData:
                fxa_update = FxaUpdatesDBModel(
                    aircraft_id=tmi_flight_list.flight,
                    update_time=fxa_flight.createTm,
                    fcaId=fxa_flight.fcaId,
                    fcaName=fxa_flight.fcaName,
                    lastUpdate=fxa_flight.lastUpdate,
                    bentryTm=fxa_flight.bentryTm,
                    createTm=fxa_flight.createTm,
                    eentryTm=fxa_flight.eentryTm,
                    entryTm=fxa_flight.entryTm,
                    exitTm=fxa_flight.exitTm,
                    extendedExitTm=fxa_flight.extendedExitTm,
                    ientryTm=fxa_flight.ientryTm,
                    oentryTm=fxa_flight.oentryTm,
                    entryLat=fxa_flight.entryLat,
                    entryLon=fxa_flight.entryLon,
                    entryHeading=fxa_flight.entryHeading,
                    exitInd=fxa_flight.exitInd,
                )
                session.add(fxa_update)
            session.commit()
    except Exception as e:
        logger.error(f"Error storing TMI_FLIGHT_LIST data: {e}", exc_info=True)
