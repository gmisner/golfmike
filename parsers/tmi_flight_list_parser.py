from typing import Optional, List
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


def parse_tmi_flight_list(flight_data_str: str) -> Optional[TmiFlightListModel]:
    """Parses TMI Flight Data from the XML string."""
    try:
        flight_data_bytes = flight_data_str.encode("utf-8")
        root = etree.fromstring(flight_data_bytes)

        # Extract flight information
        flights: List[FlightDataType] = []
        for flight_data in root.xpath(".//ns12:flightData", namespaces=NAMESPACES):
            flight_info = {}
            aircraft_id = flight_data.xpath(".//ns7:aircraftId", namespaces=NAMESPACES)
            gufi = flight_data.xpath(".//ns7:gufi", namespaces=NAMESPACES)
            igtd = flight_data.xpath(".//ns7:igtd", namespaces=NAMESPACES)
            departure_point = flight_data.xpath(
                ".//ns7:departurePoint/ns7:airport", namespaces=NAMESPACES
            )
            arrival_point = flight_data.xpath(
                ".//ns7:arrivalPoint/ns7:airport", namespaces=NAMESPACES
            )
            flight_reference = flight_data.xpath(
                ".//ns9:flightReference", namespaces=NAMESPACES
            )
            status = flight_data.xpath(".//ns9:status", namespaces=NAMESPACES)

            if aircraft_id:
                flight_info["aircraftId"] = aircraft_id[0].text
            if gufi:
                flight_info["gufi"] = gufi[0].text
            if igtd:
                flight_info["igtd"] = igtd[0].text
            if departure_point:
                flight_info["departurePoint"] = departure_point[0].text
            if arrival_point:
                flight_info["arrivalPoint"] = arrival_point[0].text
            if flight_reference:
                flight_info["flightReference"] = flight_reference[0].text
            if status:
                flight_info["status"] = status[0].text

            flight = FlightDataType(**flight_info)
            flights.append(flight)

        # Extract TMI flight info list
        tmi_flight_info_list = root.xpath(
            ".//ns9:tmiFlightInfoList", namespaces=NAMESPACES
        )
        tmi_info = None
        fxa_flight_data = []
        if tmi_flight_info_list:
            tmi_element = tmi_flight_info_list[0].xpath(
                ".//ns9:tmi", namespaces=NAMESPACES
            )
            if tmi_element:
                tmi_info = Tmi(
                    updateType=tmi_element[0].get("updateType"),
                    lastUpdateTime=tmi_element[0].get("lastUpdateTime"),
                    fcaId=(
                        tmi_element[0]
                        .xpath(".//ns9:fcaId", namespaces=NAMESPACES)[0]
                        .text
                        if tmi_element[0].xpath(".//ns9:fcaId", namespaces=NAMESPACES)
                        else None
                    ),
                )

            fxa_flight_data_elements = tmi_flight_info_list[0].xpath(
                ".//ns9:fxaFlightData/ns9:fxaFlight", namespaces=NAMESPACES
            )
            for fxa_flight in fxa_flight_data_elements:
                fxa_flight_data.append(
                    FxaFlight(
                        fcaId=(
                            fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:fcaId", namespaces=NAMESPACES
                            )[0].text
                            if fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:fcaId", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        fcaName=(
                            fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:fcaName", namespaces=NAMESPACES
                            )[0].text
                            if fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:fcaName", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        lastUpdate=(
                            fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:lastUpdate", namespaces=NAMESPACES
                            )[0].text
                            if fxa_flight.xpath(
                                ".//ns9:fxaId/ns11:lastUpdate", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        bentryTm=(
                            fxa_flight.xpath(".//ns9:bentryTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:bentryTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        createTm=(
                            fxa_flight.xpath(".//ns9:createTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:createTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        eentryTm=(
                            fxa_flight.xpath(".//ns9:eentryTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:eentryTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        entryTm=(
                            fxa_flight.xpath(".//ns9:entryTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(".//ns9:entryTm", namespaces=NAMESPACES)
                            else None
                        ),
                        exitTm=(
                            fxa_flight.xpath(".//ns9:exitTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(".//ns9:exitTm", namespaces=NAMESPACES)
                            else None
                        ),
                        extendedExitTm=(
                            fxa_flight.xpath(
                                ".//ns9:extendedExitTm", namespaces=NAMESPACES
                            )[0].text
                            if fxa_flight.xpath(
                                ".//ns9:extendedExitTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        ientryTm=(
                            fxa_flight.xpath(".//ns9:ientryTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:ientryTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        oentryTm=(
                            fxa_flight.xpath(".//ns9:oentryTm", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:oentryTm", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        entryLat=(
                            fxa_flight.xpath(".//ns9:entryLat", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:entryLat", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        entryLon=(
                            fxa_flight.xpath(".//ns9:entryLon", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(
                                ".//ns9:entryLon", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        entryHeading=(
                            fxa_flight.xpath(
                                ".//ns9:entryHeading", namespaces=NAMESPACES
                            )[0].text
                            if fxa_flight.xpath(
                                ".//ns9:entryHeading", namespaces=NAMESPACES
                            )
                            else None
                        ),
                        exitInd=(
                            fxa_flight.xpath(".//ns9:exitInd", namespaces=NAMESPACES)[
                                0
                            ].text
                            if fxa_flight.xpath(".//ns9:exitInd", namespaces=NAMESPACES)
                            else None
                        ),
                    )
                )

        tmi_flight_info = TmiFlightInfoList(
            tmi=tmi_info, fxaFlightData=FxaFlightData(fxaFlight=fxa_flight_data)
        )

        return TmiFlightListModel(flight=flights, tmiFlightInfoList=tmi_flight_info)
    except Exception as e:
        logger.error(f"Error parsing TMI Flight Data: {e}", exc_info=True)
        return None
