from lxml import etree
from models.pydantic.tmi_flight_list import TMIFlightListModel
from utils.logger import main_logger as logger

# Namespace mappings
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


# Main parser function
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


# Extract flight data with checks for missing elements
def extract_flight_data(flight_data, nsmap):
    flight_info = {}

    # Check each XML element and handle missing elements
    aircraft_id = flight_data.find(".//ns7:aircraftId", namespaces=nsmap)
    flight_info["aircraft_id"] = aircraft_id.text if aircraft_id is not None else None

    gufi = flight_data.find(".//ns7:gufi", namespaces=nsmap)
    flight_info["gufi"] = gufi.text if gufi is not None else None

    igtd = flight_data.find(".//ns7:igtd", namespaces=nsmap)
    flight_info["igtd"] = igtd.text if igtd is not None else None

    departure_airport = flight_data.find(
        ".//ns7:departurePoint/ns7:airport", namespaces=nsmap
    )
    flight_info["departure_airport"] = (
        departure_airport.text if departure_airport is not None else None
    )

    arrival_airport = flight_data.find(
        ".//ns7:arrivalPoint/ns7:airport", namespaces=nsmap
    )
    flight_info["arrival_airport"] = (
        arrival_airport.text if arrival_airport is not None else None
    )

    # Extract fxa_flights
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


# Extract individual fxa flight data with safety checks
def extract_fxa_flight_data(fxa_flight, nsmap):
    fxa_flight_data = {}

    # Check each element in fxa_flight for existence before accessing text
    fxa_id = fxa_flight.find(".//ns9:fxaId", namespaces=nsmap)
    if fxa_id is not None:
        fca_id = fxa_id.find(".//ns11:fcaId", namespaces=nsmap)
        fxa_flight_data["fcaId"] = fca_id.text if fca_id is not None else None

        fca_name = fxa_id.find(".//ns11:fcaName", namespaces=nsmap)
        fxa_flight_data["fcaName"] = fca_name.text if fca_name is not None else None

        last_update = fxa_id.find(".//ns11:lastUpdate", namespaces=nsmap)
        fxa_flight_data["lastUpdate"] = (
            last_update.text if last_update is not None else None
        )

    # Handle remaining elements with conditional checks
    bentry_tm = fxa_flight.find(".//ns9:bentryTm", namespaces=nsmap)
    fxa_flight_data["bentryTm"] = bentry_tm.text if bentry_tm is not None else None

    create_tm = fxa_flight.find(".//ns9:createTm", namespaces=nsmap)
    fxa_flight_data["createTm"] = create_tm.text if create_tm is not None else None

    eentry_tm = fxa_flight.find(".//ns9:eentryTm", namespaces=nsmap)
    fxa_flight_data["eentryTm"] = eentry_tm.text if eentry_tm is not None else None

    entry_lat = fxa_flight.find(".//ns9:entryLat", namespaces=nsmap)
    fxa_flight_data["entryLat"] = (
        float(entry_lat.text) if entry_lat is not None else None
    )

    entry_lon = fxa_flight.find(".//ns9:entryLon", namespaces=nsmap)
    fxa_flight_data["entryLon"] = (
        float(entry_lon.text) if entry_lon is not None else None
    )

    entry_heading = fxa_flight.find(".//ns9:entryHeading", namespaces=nsmap)
    fxa_flight_data["entryHeading"] = (
        int(entry_heading.text) if entry_heading is not None else None
    )

    exit_ind = fxa_flight.find(".//ns9:exitInd", namespaces=nsmap)
    fxa_flight_data["exitInd"] = exit_ind.text if exit_ind is not None else None

    return fxa_flight_data
