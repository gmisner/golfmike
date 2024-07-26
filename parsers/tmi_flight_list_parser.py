from lxml import etree
from models.pydantic.tmi_flight_list import TMIFlightListModel
from utils.logger import main_logger as logger

NAMESPACES = {
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns2": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns4": "urn:us:gov:dot:faa:atm:tfm:ficommondatatypes",
    "ns3": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "ns6": "http://www.fixm.aero/tfm/3.1",
    "ns5": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "ns8": "http://www.faa.aero/nas/3.1",
    "ns7": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "ns13": "urn:us:gov:dot:faa:atm:tfm:rapttimeline",
    "ns9": "urn:us:gov:dot:faa:atm:tfm:ficommondmessages2",
    "ns12": "urn:us:gov:dot:faa:atm:tfm:flowinformation",
    "ns11": "urn:us:gov:dot:faa:atm:tfm:ficommondmessages",
    "ns10": "urn:us:gov:dot:faa:atm:tfm:tfmrequestreplytypes",
    "ns16": "http://www.fixm.aero/flight/3.0",
    "ns15": "http://www.fixm.aero/foundation/3.0",
    "ns14": "http://www.fixm.aero/base/3.0",
}


def parse_tmi_flight_list(xml_bytes: bytes):
    try:
        root = etree.fromstring(xml_bytes)
        logger.debug("Root of XML parsed")

        fi_outputs = root.findall(".//ns5:fiOutput", namespaces=NAMESPACES)
        if not fi_outputs:
            raise ValueError("fiOutput element not found")

        logger.debug("Found fiOutput element")

        flight_list = []
        for fi_output in fi_outputs:
            fi_message = fi_output.find(".//ns12:fiMessage", namespaces=NAMESPACES)
            if (
                fi_message is not None
                and fi_message.get("msgType") == "TMI_FLIGHT_LIST"
            ):
                logger.debug(f"Message type: {fi_message.get('msgType')}")
                tmi_flight_data_list = fi_message.find(
                    ".//ns12:tmiFlightDataList", namespaces=NAMESPACES
                )
                if tmi_flight_data_list is not None:
                    for flight_data in tmi_flight_data_list.findall(
                        ".//ns12:flightData", namespaces=NAMESPACES
                    ):
                        flight = extract_flight_data(flight_data, NAMESPACES)
                        flight_list.append(flight)

        logger.info(f"Parsed TMI flight list: {flight_list}")
        return flight_list

    except Exception as e:
        logger.error(f"Failed to parse XML data: {e}", exc_info=True)
        raise


def extract_flight_data(flight_data, nsmap):
    flight_info = {}
    flight_info["aircraft_id"] = flight_data.find(
        ".//ns7:aircraftId", namespaces=nsmap
    ).text
    flight_info["gufi"] = flight_data.find(".//ns7:gufi", namespaces=nsmap).text
    flight_info["igtd"] = flight_data.find(".//ns7:igtd", namespaces=nsmap).text
    flight_info["departure_airport"] = flight_data.find(
        ".//ns7:departurePoint/ns7:airport", namespaces=nsmap
    ).text
    flight_info["arrival_airport"] = flight_data.find(
        ".//ns7:arrivalPoint/ns7:airport", namespaces=nsmap
    ).text

    fxa_flights = []
    tmi_flight_info_list = flight_data.find(
        ".//ns9:tmiFlightInfoList", namespaces=nsmap
    )
    if tmi_flight_info_list is not None:
        for fxa_flight in tmi_flight_info_list.findall(
            ".//ns9:fxaFlight", namespaces=nsmap
        ):
            fxa_flight_data = extract_fxa_flight_data(fxa_flight, nsmap)
            fxa_flights.append(fxa_flight_data)

    flight_info["fxa_flights"] = fxa_flights
    return flight_info


def extract_fxa_flight_data(fxa_flight, nsmap):
    fxa_flight_data = {}
    fxa_id = fxa_flight.find(".//ns9:fxaId", namespaces=nsmap)
    fxa_flight_data["fxaId"] = fxa_id.find(".//ns11:fcaId", namespaces=nsmap).text
    fxa_flight_data["fcaName"] = fxa_id.find(".//ns11:fcaName", namespaces=nsmap).text
    fxa_flight_data["lastUpdate"] = fxa_id.find(
        ".//ns11:lastUpdate", namespaces=nsmap
    ).text
    fxa_flight_data["bentryTm"] = fxa_flight.find(
        ".//ns9:bentryTm", namespaces=nsmap
    ).text
    fxa_flight_data["createTm"] = fxa_flight.find(
        ".//ns9:createTm", namespaces=nsmap
    ).text
    fxa_flight_data["eentryTm"] = fxa_flight.find(
        ".//ns9:eentryTm", namespaces=nsmap
    ).text
    fxa_flight_data["entryTm"] = fxa_flight.find(
        ".//ns9:entryTm", namespaces=nsmap
    ).text
    fxa_flight_data["exitTm"] = fxa_flight.find(".//ns9:exitTm", namespaces=nsmap).text
    fxa_flight_data["extendedExitTm"] = fxa_flight.find(
        ".//ns9:extendedExitTm", namespaces=nsmap
    ).text
    fxa_flight_data["ientryTm"] = fxa_flight.find(
        ".//ns9:ientryTm", namespaces=nsmap
    ).text
    fxa_flight_data["oentryTm"] = fxa_flight.find(
        ".//ns9:oentryTm", namespaces=nsmap
    ).text
    fxa_flight_data["entryLat"] = float(
        fxa_flight.find(".//ns9:entryLat", namespaces=nsmap).text
    )
    fxa_flight_data["entryLon"] = float(
        fxa_flight.find(".//ns9:entryLon", namespaces=nsmap).text
    )
    fxa_flight_data["entryHeading"] = int(
        fxa_flight.find(".//ns9:entryHeading", namespaces=nsmap).text
    )
    fxa_flight_data["exitInd"] = fxa_flight.find(
        ".//ns9:exitInd", namespaces=nsmap
    ).text
    return fxa_flight_data
