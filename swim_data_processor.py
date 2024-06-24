import xmltodict
import logging
from datetime import datetime
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert

from pydantic_models import *

from models import (
    Session,
    AircraftDBModel,
    FlightPlanDBModel,
    WaypointDBModel,
    TmiUpdatesDBModel,
    FxaUpdatesDBModel,
)

logger = logging.getLogger(__name__)


def parse_xml_to_pydantic(xml_data):
    try:
        # Log the received XML data (Consider a separate log file)
        logger.debug(f"Received XML Data: {xml_data}")

        xml_dict = xmltodict.parse(
            xml_data,
            process_namespaces=True,
            namespaces={
                "urn:us:gov:dot:faa:atm:tfm:tfmdataservice": None,
                "urn:us:gov:dot:faa:atm:tfm:flowinformation": None,
                "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2": None,
                "urn:us:gov:dot:faa:atm:tfm:flightdata": None,
                "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements": None,
                "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages": None,
            },
        )

        if "tfmDataService" in xml_dict:
            tfm_data = xml_dict["tfmDataService"]

            if "fiOutput" in tfm_data:
                fi_message = tfm_data["fiOutput"]["fiMessage"]
                msg_type = fi_message.get("@msgType")

                # Log message type
                logger.debug(f"Processing message type: {msg_type}")

                if msg_type == "TMI_FLIGHT_LIST":
                    return handle_tmi_flight_list(fi_message)
                elif msg_type == "FlightSectors":
                    return handle_flight_sectors(fi_message)
                else:
                    logger.warning(
                        f"Unknown message type: {msg_type}. Skipping message."
                    )
        else:
            logger.warning(f"Unknown XML structure. No 'tfmDataService' element found.")
        return None

    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        # Log the problematic XML (excerpt) - sanitize if necessary
        logger.error(
            f"Problematic XML (excerpt): {xml_data[:500]}..."
        )  # Log first 500 chars
        return None


def handle_track_information(fltd_message):
    # Extract relevant data for TrackInformationModel
    pass


def handle_oceanic_report(fltd_message):
    # Extract relevant data for OceanicReportModel
    pass


def handle_tmi_flight_list(fi_message):
    flight_data_list = fi_message.get("tmiFlightDataList", {}).get("flightData", [])
    if not isinstance(flight_data_list, list):
        flight_data_list = [flight_data_list]

    parsed_flights = []
    for flight_data in flight_data_list:
        if isinstance(flight_data, dict):
            flight = flight_data.get("flight", {})
            aircraft_id = flight.get("aircraftId")
            gufi = flight.get("gufi")
            igtd = flight.get("igtd")
            if igtd:
                try:
                    igtd = datetime.fromisoformat(igtd)
                except ValueError:
                    igtd = None

            departure_point_data = flight.get("departurePoint", {})
            departure_point = (
                Airport(**departure_point_data) if departure_point_data else None
            )

            arrival_point_data = flight.get("arrivalPoint", {})
            arrival_point = (
                Airport(**arrival_point_data) if arrival_point_data else None
            )

            tmi_flight_info_list = flight_data.get("tmiFlightInfoList", {}).get(
                "tmi", []
            )
            if not isinstance(tmi_flight_info_list, list):
                tmi_flight_info_list = [tmi_flight_info_list]

            fxa_flight_data_list = (
                flight_data.get("tmiFlightInfoList", {})
                .get("fxaFlightData", {})
                .get("fxaFlight", [])
            )
            if not isinstance(fxa_flight_data_list, list):
                fxa_flight_data_list = [fxa_flight_data_list]

            flight_reference = flight_data.get("flightReference")
            status = flight_data.get("status")

            tmi_data_list = []
            for tmi_item in tmi_flight_info_list:
                if isinstance(tmi_item, dict):
                    tmi_update_type = tmi_item.get("@updateType", "UNKNOWN")
                    tmi_last_update_time = tmi_item.get("@lastUpdateTime")
                    tmi_fca_id = tmi_item.get("fcaId")

                    if tmi_last_update_time:
                        try:
                            tmi_last_update_time = datetime.fromisoformat(
                                tmi_last_update_time
                            ).isoformat()
                        except ValueError:
                            tmi_last_update_time = datetime.now().isoformat()

                    tmi_data = Tmi(
                        updateType=tmi_update_type,
                        lastUpdateTime=tmi_last_update_time,
                        fcaId=tmi_fca_id,
                    )
                    tmi_data_list.append(tmi_data)

            fxa_flight_data = []
            for fxa_flight_item in fxa_flight_data_list:
                if isinstance(fxa_flight_item, dict):
                    fxa_id_data = fxa_flight_item.get("fxaId", {})
                    fxa_id = {
                        "fcaId": fxa_id_data.get("fcaId", "UNKNOWN"),
                        "fcaName": fxa_id_data.get("fcaName", "UNKNOWN"),
                        "lastUpdate": fxa_id_data.get(
                            "lastUpdate", datetime.now().isoformat()
                        ),
                    }

                    fxa_flight = FxaFlight(
                        fxaId=fxa_id,
                        bentryTm=fxa_flight_item.get("bentryTm"),
                        createTm=fxa_flight_item.get("createTm"),
                        eentryTm=fxa_flight_item.get("eentryTm"),
                        entryTm=fxa_flight_item.get("entryTm"),
                        exitTm=fxa_flight_item.get("exitTm"),
                        extendedExitTm=fxa_flight_item.get("extendedExitTm"),
                        ientryTm=fxa_flight_item.get("ientryTm"),
                        oentryTm=fxa_flight_item.get("oentryTm"),
                        entryLat=fxa_flight_item.get("entryLat"),
                        entryLon=fxa_flight_item.get("entryLon"),
                        entryHeading=fxa_flight_item.get("entryHeading"),
                        exitInd=fxa_flight_item.get("exitInd"),
                    )
                    fxa_flight_data.append(fxa_flight)

            try:
                return TmiFlightListModel(
                    id=aircraft_id,
                    sensitivity=fi_message.get("@sensitivity"),
                    visDomain=fi_message.get("@visDomain"),
                    destinationCodes=fi_message.get("@destinationCodes"),
                    sourceFacility=fi_message.get("@sourceFacility"),
                    sourceTimeStamp=fi_message.get("@sourceTimeStamp"),
                    msgType=fi_message.get("@msgType"),
                    aircraftId=aircraft_id,
                    gufi=gufi,
                    igtd=igtd,
                    departurePoint=departure_point,
                    arrivalPoint=arrival_point,
                    flightReference=flight_reference,
                    status=status,
                    tmiFlightInfoList=tmi_data_list,
                    fxaFlightData=fxa_flight_data,
                )
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                return None
        else:
            logger.warning(
                "Unexpected data format for 'flight_data'. It's not a dictionary. Skipping this entry."
            )
    return None


def handle_flight_sectors(fi_message):
    flight_data_list = fi_message.get("tmiFlightDataList", {}).get("flightData", [])
    if not isinstance(flight_data_list, list):
        flight_data_list = [flight_data_list]

    parsed_flights = []
    for flight_data in flight_data_list:
        if isinstance(flight_data, dict):
            aircraft_id = flight_data.get("@acid")
            gufi = (
                flight_data.get("ncsmFlightSectors", {})
                .get("qualifiedAircraftId", {})
                .get("gufi")
            )
            igtd = (
                flight_data.get("ncsmFlightSectors", {})
                .get("qualifiedAircraftId", {})
                .get("igtd")
            )
            if igtd:
                try:
                    igtd = datetime.fromisoformat(igtd)
                except ValueError:
                    igtd = None

            departure_point_data = (
                flight_data.get("ncsmFlightSectors", {})
                .get("qualifiedAircraftId", {})
                .get("departurePoint", {})
            )
            departure_point = (
                Airport(**departure_point_data) if departure_point_data else None
            )

            arrival_point_data = (
                flight_data.get("ncsmFlightSectors", {})
                .get("qualifiedAircraftId", {})
                .get("arrivalPoint", {})
            )
            arrival_point = (
                Airport(**arrival_point_data) if arrival_point_data else None
            )

            flight_traversal_data = flight_data.get("ncsmFlightSectors", {}).get(
                "flightTraversalData2", {}
            )

            sectors = flight_traversal_data.get("sector", [])
            if not isinstance(sectors, list):
                sectors = [sectors]

            sector_list = []
            for sector in sectors:
                sector_data = {
                    "name": sector.get("#text"),
                    "sequenceNumber": sector.get("@sequenceNumber"),
                    "elapsedEntryTime": sector.get("@elapsedEntryTime"),
                }
                sector_list.append(sector_data)

            return FlightSectorsModel(
                id=aircraft_id,
                sensitivity=fi_message.get("@sensitivity"),
                sourceFacility=fi_message.get("@sourceFacility"),
                sourceTimeStamp=fi_message.get("@sourceTimeStamp"),
                msgType=fi_message.get("@msgType"),
                aircraftId=aircraft_id,
                gufi=gufi,
                departurePoint=departure_point,
                arrivalPoint=arrival_point,
                sectorDesignator=None,  # Add if applicable
                sectorEntryTime=None,  # Add if applicable
                sectorExitTime=None,  # Add if applicable
                entryPoint=None,  # Add if applicable
                exitPoint=None,  # Add if applicable
                crossingAltitude=None,  # Add if applicable
                crossingSpeed=None,  # Add if applicable
                flightLevel=None,  # Add if applicable
                routeOfFlight=None,  # Add if applicable
                trajectory=sector_list,
            )
    return parsed_flights


def parse_and_store_to_database(xml_data):
    parsed_data = parse_xml_to_pydantic(xml_data)
    if parsed_data is not None:
        try:
            flight_data_dict = parsed_data.dict()

            if isinstance(parsed_data, TmiFlightListModel):
                tmi_data_list = flight_data_dict.pop("tmiFlightInfoList", [])
                fxa_flight_data = flight_data_dict.pop("fxaFlightData", [])

                with Session() as session:
                    # Store or update aircraft data
                    aircraft_data = {
                        "aircraft_id": flight_data_dict["aircraftId"],
                        "gufi": flight_data_dict["gufi"],
                        "flight_reference": flight_data_dict["flightReference"],
                        "status": flight_data_dict["status"],
                    }
                    stmt = insert(AircraftDBModel.__table__).values(**aircraft_data)
                    update_dict = {c.name: c for c in stmt.excluded}
                    update_stmt = stmt.on_conflict_do_update(
                        index_elements=["aircraft_id"], set_=update_dict
                    )
                    session.execute(update_stmt)

                    # Store flight plan
                    departure_point = flight_data_dict.get("departurePoint")
                    arrival_point = flight_data_dict.get("arrivalPoint")
                    departure_airport = (
                        departure_point.get("airport") if departure_point else None
                    )
                    arrival_airport = (
                        arrival_point.get("airport") if arrival_point else None
                    )
                    flight_plan_data = {
                        "aircraft_id": flight_data_dict["aircraftId"],
                        "departure_airport": departure_airport,
                        "arrival_airport": arrival_airport,
                        "igtd": flight_data_dict.get("igtd"),
                    }
                    stmt = insert(FlightPlanDBModel.__table__).values(
                        **flight_plan_data
                    )
                    update_dict = {c.name: c for c in stmt.excluded}
                    update_stmt = stmt.on_conflict_do_update(
                        index_elements=["aircraft_id"], set_=update_dict
                    )
                    session.execute(update_stmt)

                    # Store TMI updates
                    for tmi in tmi_data_list:
                        update_time = (
                            flight_data_dict.get("sourceTimeStamp")
                            or datetime.now().isoformat()
                        )
                        tmi_data = {
                            "aircraft_id": flight_data_dict["aircraftId"],
                            "update_time": update_time,
                            "update_type": tmi["updateType"],
                            "last_update_time": tmi["lastUpdateTime"],
                            "fca_id": tmi["fcaId"],
                        }
                        stmt = insert(TmiUpdatesDBModel.__table__).values(**tmi_data)
                        update_dict = {c.name: c for c in stmt.excluded}
                        update_stmt = stmt.on_conflict_do_update(
                            index_elements=["aircraft_id", "update_time"],
                            set_=update_dict,
                        )
                        session.execute(update_stmt)

                    # Store FXA updates
                    for fxa in fxa_flight_data:
                        update_time = (
                            flight_data_dict.get("sourceTimeStamp")
                            or datetime.now().isoformat()
                        )
                        fxa_data = {
                            "aircraft_id": flight_data_dict["aircraftId"],
                            "update_time": update_time,
                            "fxa_id": json.dumps(
                                fxa["fxaId"]
                            ),  # Convert to JSON string
                            "entry_time": fxa["entryTm"],
                            "create_time": fxa["createTm"],
                            "exit_time": fxa["exitTm"],
                            "entry_lat": fxa["entryLat"],
                            "entry_lon": fxa["entryLon"],
                            "entry_heading": fxa["entryHeading"],
                            "exit_ind": fxa["exitInd"],
                        }
                        stmt = insert(FxaUpdatesDBModel.__table__).values(**fxa_data)
                        update_dict = {c.name: c for c in stmt.excluded}
                        update_stmt = stmt.on_conflict_do_update(
                            index_elements=["aircraft_id", "update_time"],
                            set_=update_dict,
                        )
                        session.execute(update_stmt)

                    session.commit()

            logger.info(f"Successfully stored data.")
        except IntegrityError as e:
            logger.error(f"Integrity error storing to database: {e}", exc_info=True)
            session.rollback()
        except Exception as e:
            logger.error(f"Error storing to database: {e}", exc_info=True)
            session.rollback()
    else:
        logger.error("Failed to parse XML data.")


def store_parsed_data(parsed_data):
    flight_data_dict = parsed_data.dict()

    with Session() as session:
        # Store or update aircraft data
        aircraft_data = {
            "aircraft_id": flight_data_dict["aircraftId"],
            "gufi": flight_data_dict["gufi"],
            "flight_reference": flight_data_dict["flightReference"],
            "status": flight_data_dict["status"],
        }
        stmt = insert(AircraftDBModel).values(**aircraft_data)
        update_dict = {c.name: c for c in stmt.excluded}
        update_stmt = stmt.on_conflict_do_update(
            index_elements=["aircraft_id"], set_=update_dict
        )
        session.execute(update_stmt)

        # Store flight plan
        departure_point = flight_data_dict.get("departurePoint")
        arrival_point = flight_data_dict.get("arrivalPoint")
        departure_airport = departure_point.get("airport") if departure_point else None
        arrival_airport = arrival_point.get("airport") if arrival_point else None
        flight_plan_data = {
            "aircraft_id": flight_data_dict["aircraftId"],
            "departure_airport": departure_airport,
            "arrival_airport": arrival_airport,
            "igtd": flight_data_dict.get("igtd"),
        }
        stmt = insert(FlightPlanDBModel).values(**flight_plan_data)
        update_dict = {c.name: c for c in stmt.excluded}
        update_stmt = stmt.on_conflict_do_update(
            index_elements=["aircraft_id"], set_=update_dict
        )
        session.execute(update_stmt)

        # Store TMI updates
        for tmi in flight_data_dict.get("tmiFlightInfoList", []):
            update_time = (
                flight_data_dict.get("sourceTimeStamp") or datetime.now().isoformat()
            )
            tmi_data = {
                "aircraft_id": flight_data_dict["aircraftId"],
                "update_time": update_time,
                "update_type": tmi["updateType"],
                "last_update_time": tmi["lastUpdateTime"],
                "fca_id": tmi["fcaId"],
            }
            stmt = insert(TmiUpdatesDBModel).values(**tmi_data)
            update_dict = {c.name: c for c in stmt.excluded}
            update_stmt = stmt.on_conflict_do_update(
                index_elements=["aircraft_id", "update_time"], set_=update_dict
            )
            session.execute(update_stmt)

        # Store FXA updates
        for fxa in flight_data_dict.get("fxaFlightData", []):
            update_time = (
                flight_data_dict.get("sourceTimeStamp") or datetime.now().isoformat()
            )
            fxa_data = {
                "aircraft_id": flight_data_dict["aircraftId"],
                "update_time": update_time,
                "fxa_id": fxa["fxaId"]["fcaId"],
                "entry_time": fxa["entryTm"],
                "create_time": fxa["createTm"],
                "exit_time": fxa["exitTm"],
                "entry_lat": fxa["entryLat"],
                "entry_lon": fxa["entryLon"],
                "entry_heading": fxa["entryHeading"],
                "exit_ind": fxa["exitInd"],
            }
            stmt = insert(FxaUpdatesDBModel).values(**fxa_data)
            update_dict = {c.name: c for c in stmt.excluded}
            update_stmt = stmt.on_conflict_do_update(
                index_elements=["aircraft_id", "update_time"], set_=update_dict
            )
            session.execute(update_stmt)
            session.commit()

            logger.info(f"Successfully stored data.")
