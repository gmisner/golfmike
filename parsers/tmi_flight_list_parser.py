from typing import Optional
from lxml import etree
from models.pydantic.tmi_flight_list import (
    TmiFlightListModel,
    FlightDataType,
    TmiFlightInfoList,
    Tmi,
    FxaFlightData,
    FxaFlight,
)
from utils.logger import main_logger as logger

NAMESPACES = {
    "ns2": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns3": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "ns4": "urn:us:gov:dot:faa:atm:tfm:ficommondatatypes",
    "ns5": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "ns6": "http://www.fixm.aero/tfm/3.1",
    "ns7": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "ns8": "http://www.faa.aero/nas/3.1",
    "ns9": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2",
    "ns10": "urn:us:gov:dot:faa:atm:tfm:tfmrequestreplytypes",
    "ns11": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages",
    "ns12": "urn:us:gov:dot:faa:atm:tfm:flowinformation",
    "ns13": "urn:us:gov:dot:faa:atm:tfm:rapttimeline",
    "ns14": "http://www.fixm.aero/flight/3.0",
    "ns15": "http://www.fixm.aero/foundation/3.0",
    "ns16": "http://www.fixm.aero/base/3.0",
}


def parse_tmi_flight_data(flight_data: etree.Element) -> Optional[TmiFlightListModel]:
    """Parses TMI Flight Data from the XML element."""
    try:
        # Extract flight information
        flight_info = {}
        aircraft_id = flight_data.find(
            "ns9:flight/ns7:aircraftId", namespaces=NAMESPACES
        )
        gufi = flight_data.find("ns9:flight/ns7:gufi", namespaces=NAMESPACES)
        igtd = flight_data.find("ns9:flight/ns7:igtd", namespaces=NAMESPACES)
        departure_point = flight_data.find(
            "ns9:flight/ns7:departurePoint/ns7:airport", namespaces=NAMESPACES
        )
        arrival_point = flight_data.find(
            "ns9:flight/ns7:arrivalPoint/ns7:airport", namespaces=NAMESPACES
        )
        flight_reference = flight_data.find(
            "ns9:flightReference", namespaces=NAMESPACES
        )
        status = flight_data.find("ns9:status", namespaces=NAMESPACES)

        if aircraft_id is not None:
            flight_info["aircraftId"] = aircraft_id.text
        if gufi is not None:
            flight_info["gufi"] = gufi.text
        if igtd is not None:
            flight_info["igtd"] = igtd.text
        if departure_point is not None:
            flight_info["departurePoint"] = departure_point.text
        if arrival_point is not None:
            flight_info["arrivalPoint"] = arrival_point.text
        if flight_reference is not None:
            flight_info["flightReference"] = flight_reference.text
        if status is not None:
            flight_info["status"] = status.text

        flight = FlightDataType(**flight_info)

        # Extract TMI flight info list
        tmi_flight_info_list = flight_data.find(
            "ns9:tmiFlightInfoList", namespaces=NAMESPACES
        )
        tmi_info = None
        fxa_flight_data = []
        if tmi_flight_info_list is not None:
            tmi_element = tmi_flight_info_list.find("ns9:tmi", namespaces=NAMESPACES)
            if tmi_element is not None:
                tmi_info = Tmi(
                    updateType=tmi_element.get("updateType"),
                    lastUpdateTime=tmi_element.get("lastUpdateTime"),
                    fcaId=(
                        tmi_element.find("ns9:fcaId", namespaces=NAMESPACES).text
                        if tmi_element.find("ns9:fcaId", namespaces=NAMESPACES)
                        is not None
                        else None
                    ),
                )

            fxa_flight_data_elements = tmi_flight_info_list.findall(
                "ns9:fxaFlightData/ns9:fxaFlight", namespaces=NAMESPACES
            )
            for fxa_flight in fxa_flight_data_elements:
                fxa_flight_data.append(
                    FxaFlight(
                        fcaId=(
                            fxa_flight.find(
                                "ns9:fxaId/ns11:fcaId", namespaces=NAMESPACES
                            ).text
                            if fxa_flight.find(
                                "ns9:fxaId/ns11:fcaId", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        fcaName=(
                            fxa_flight.find(
                                "ns9:fxaId/ns11:fcaName", namespaces=NAMESPACES
                            ).text
                            if fxa_flight.find(
                                "ns9:fxaId/ns11:fcaName", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        lastUpdate=(
                            fxa_flight.find(
                                "ns9:fxaId/ns11:lastUpdate", namespaces=NAMESPACES
                            ).text
                            if fxa_flight.find(
                                "ns9:fxaId/ns11:lastUpdate", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        bentryTm=(
                            fxa_flight.find("ns9:bentryTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:bentryTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        createTm=(
                            fxa_flight.find("ns9:createTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:createTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        eentryTm=(
                            fxa_flight.find("ns9:eentryTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:eentryTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        entryTm=(
                            fxa_flight.find("ns9:entryTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:entryTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        exitTm=(
                            fxa_flight.find("ns9:exitTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:exitTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        extendedExitTm=(
                            fxa_flight.find(
                                "ns9:extendedExitTm", namespaces=NAMESPACES
                            ).text
                            if fxa_flight.find(
                                "ns9:extendedExitTm", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        ientryTm=(
                            fxa_flight.find("ns9:ientryTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:ientryTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        oentryTm=(
                            fxa_flight.find("ns9:oentryTm", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:oentryTm", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        entryLat=(
                            fxa_flight.find("ns9:entryLat", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:entryLat", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        entryLon=(
                            fxa_flight.find("ns9:entryLon", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:entryLon", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                        entryHeading=(
                            fxa_flight.find(
                                "ns9:entryHeading", namespaces=NAMESPACES
                            ).text
                            if fxa_flight.find(
                                "ns9:entryHeading", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        exitInd=(
                            fxa_flight.find("ns9:exitInd", namespaces=NAMESPACES).text
                            if fxa_flight.find("ns9:exitInd", namespaces=NAMESPACES)
                            is not None
                            else None
                        ),
                    )
                )

        tmi_flight_info = TmiFlightInfoList(
            tmi=tmi_info, fxaFlightData=FxaFlightData(fxaFlight=fxa_flight_data)
        )

        return TmiFlightListModel(flight=flight, tmiFlightInfoList=tmi_flight_info)
    except Exception as e:
        logger.error(f"Error parsing TMI Flight Data: {e}", exc_info=True)
        return None
