from lxml import etree
from sqlalchemy import create_engine, insert, exc
from sqlalchemy.orm import sessionmaker
from parsers.flight_plan_parser import parse_flight_plan
from parsers.track_information_parser import parse_track_information
from parsers.fltd_message_parser import parse_fltd_message
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.status_parser import parse_status
from parsers.flight_modify_parser import parse_flight_modify
from parsers.flight_plan_amendment_parser import parse_flight_plan_amendment
from parsers.tmi_flight_list_parser import parse_tmi_flight_data
from storers.tmi_updates_storer import store_tmi_flight_list
from storers.track_storer import store_track
from storers.fltd_message_storer import store_fltd_message
from storers.status_storer import store_status
from utils.logger import main_logger as logger
from models.pydantic.tmi_flight_list import TmiFlightListModel

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
    "ns15": "http://www.fixm.aero/base/3.0",
    "ns16": "http://www.fixm.aero/foundation/3.0",
}

# --- Parsing Functions ---


def parse_xml_to_pydantic(xml_data: str):
    """Parses XML data and returns a Pydantic model (or None if parsing fails)."""
    try:
        logger.debug(xml_data)

        # Parse the XML using lxml
        root = etree.fromstring(xml_data.encode("utf-8"))

        # Extract fiOutput (for ns5:fiMessage messages)
        fi_output = root.find("ns5:fiOutput", namespaces=NAMESPACES)

        if fi_output is not None:
            fi_messages = fi_output.findall("ns12:fiMessage", namespaces=NAMESPACES)
            parsed_data = []
            for fi_message in fi_messages:
                # Check the message type and parse accordingly
                msg_type = fi_message.get("msgType")
                if msg_type == "TMI_FLIGHT_LIST":
                    tmi_flight_data_list = fi_message.find(
                        "ns12:tmiFlightDataList", namespaces=NAMESPACES
                    )
                    if tmi_flight_data_list is not None:
                        flight_data_elements = tmi_flight_data_list.findall(
                            "ns12:flightData", namespaces=NAMESPACES
                        )
                        for flight_data in flight_data_elements:
                            parsed_message = parse_tmi_flight_data(flight_data)
                            if parsed_message:
                                parsed_data.append(parsed_message)

            return parsed_data if parsed_data else None

        logger.warning("No fiOutput or fiMessage element found in XML.")
        return None

    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_data[:500]}...")
        return None


def parse_and_store_to_database(xml_data: str):
    """Parses XML data and stores it to the database."""
    try:
        logger.debug(xml_data)

        # Parse and store the XML data
        parsed_data = parse_xml_to_pydantic(xml_data)
        if parsed_data is not None:
            if isinstance(parsed_data, list) and all(
                isinstance(item, TmiFlightListModel) for item in parsed_data
            ):
                for message in parsed_data:
                    store_tmi_flight_list(message)
            else:
                logger.error(f"Unknown parsed data type: {type(parsed_data)}")
        else:
            logger.error("Failed to parse XML data.")
    except Exception as e:
        logger.error(f"Error parsing and storing XML data: {e}")
