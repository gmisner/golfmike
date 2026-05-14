from lxml import etree
from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_tmi_flight_list(root: etree._Element):
    """Parse TMI flight list from an already-parsed XML root (single parse upstream)."""
    try:
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

    # Extract flightReference
    flight_reference = flight_data.find(".//ns9:flightReference", namespaces=nsmap)
    flight_info["flight_reference"] = (
        flight_reference.text if flight_reference is not None else None
    )

    # Extract status
    status = flight_data.find(".//ns9:status", namespaces=nsmap)
    flight_info["status"] = status.text if status is not None else None

    # Extract TMI information and fxa_flights
    tmi_list = []
    fxa_flights = []
    tmi_flight_info_list = flight_data.find("ns9:tmiFlightInfoList", namespaces=nsmap)
    if tmi_flight_info_list is not None:
        # Extract tmi elements with attributes
        for tmi in tmi_flight_info_list.findall(".//ns9:tmi", namespaces=nsmap):
            tmi_data = {
                "update_type": tmi.get("updateType"),
                "last_update_time": tmi.get("lastUpdateTime"),
            }
            fca_id = tmi.find(".//ns9:fcaId", namespaces=nsmap)
            if fca_id is not None:
                tmi_data["fca_id"] = fca_id.text
            tmi_list.append(tmi_data)

        # Extract fxa_flights from fxaFlightData
        fxa_flight_data_container = tmi_flight_info_list.find(
            "ns9:fxaFlightData", namespaces=nsmap
        )
        if fxa_flight_data_container is not None:
            for fxa_flight in fxa_flight_data_container.findall(
                "ns9:fxaFlight", namespaces=nsmap
            ):
                fxa_flight_data = extract_fxa_flight_data(fxa_flight, nsmap)
                fxa_flights.append(fxa_flight_data)

    flight_info["tmi_info"] = tmi_list
    flight_info["fxa_flights"] = fxa_flights
    return flight_info


# Extract individual fxa flight data with safety checks
def extract_fxa_flight_data(fxa_flight, nsmap):
    fxa_flight_data = {}

    # Check each element in fxa_flight for existence before accessing text
    # Search for fxaId first - it's a direct child
    fxa_id = fxa_flight.find("ns9:fxaId", namespaces=nsmap)
    if fxa_id is not None:
        # Iterate through children of fxaId to find fcaId, fcaName, lastUpdate
        ns11_uri = nsmap.get("ns11", "urn:us:gov:dot:faa:atm:tfm:ficommondessages")
        for child in fxa_id:
            tag = child.tag
            if tag.endswith("}fcaId") or tag == f"{{{ns11_uri}}}fcaId":
                fxa_flight_data["fcaId"] = child.text
            elif tag.endswith("}fcaName") or tag == f"{{{ns11_uri}}}fcaName":
                fxa_flight_data["fcaName"] = child.text
            elif tag.endswith("}lastUpdate") or tag == f"{{{ns11_uri}}}lastUpdate":
                fxa_flight_data["lastUpdate"] = child.text

    # Handle remaining elements with conditional checks
    bentry_tm = fxa_flight.find(".//ns9:bentryTm", namespaces=nsmap)
    fxa_flight_data["bentryTm"] = bentry_tm.text if bentry_tm is not None else None

    create_tm = fxa_flight.find(".//ns9:createTm", namespaces=nsmap)
    fxa_flight_data["createTm"] = create_tm.text if create_tm is not None else None

    eentry_tm = fxa_flight.find(".//ns9:eentryTm", namespaces=nsmap)
    fxa_flight_data["eentryTm"] = eentry_tm.text if eentry_tm is not None else None

    # Extract additional time fields
    entry_tm = fxa_flight.find(".//ns9:entryTm", namespaces=nsmap)
    fxa_flight_data["entryTm"] = entry_tm.text if entry_tm is not None else None

    exit_tm = fxa_flight.find(".//ns9:exitTm", namespaces=nsmap)
    fxa_flight_data["exitTm"] = exit_tm.text if exit_tm is not None else None

    extended_exit_tm = fxa_flight.find(".//ns9:extendedExitTm", namespaces=nsmap)
    fxa_flight_data["extendedExitTm"] = (
        extended_exit_tm.text if extended_exit_tm is not None else None
    )

    ientry_tm = fxa_flight.find(".//ns9:ientryTm", namespaces=nsmap)
    fxa_flight_data["ientryTm"] = ientry_tm.text if ientry_tm is not None else None

    oentry_tm = fxa_flight.find(".//ns9:oentryTm", namespaces=nsmap)
    fxa_flight_data["oentryTm"] = oentry_tm.text if oentry_tm is not None else None

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
