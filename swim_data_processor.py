from lxml import etree
from parser_storer_registry import get_parser, get_storer
from utils.logger import main_logger as logger
from db_config import SessionLocal  # Import SessionLocal

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
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",  # Add the ds prefix
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",  # Add the fdm prefix
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",  # Add the nxce prefix
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",  # Add the nxcm prefix
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",  # Add the xsi prefix
}


def parse_xml_to_pydantic(xml_data: str):
    """Parses XML data and returns a list of Pydantic models (or None if parsing fails)."""
    try:
        logger.debug(xml_data)
        root = etree.fromstring(xml_data.encode("utf-8"))

        parsed_data = []

        # Check for different root elements and parse accordingly
        fi_output = root.find("ns5:fiOutput", namespaces=NAMESPACES)
        fltd_output = root.find("ds:fltdOutput", namespaces=NAMESPACES)

        if fi_output is not None:
            fi_messages = fi_output.findall("ns12:fiMessage", namespaces=NAMESPACES)
            for fi_message in fi_messages:
                msg_type = fi_message.get("msgType")
                parser = get_parser(msg_type)
                if parser:
                    parsed_message = parser(
                        etree.tostring(fi_message, encoding="unicode")
                    )
                    if parsed_message:
                        parsed_data.append(parsed_message)
                else:
                    logger.warning(f"No parser registered for message type: {msg_type}")

        elif fltd_output is not None:
            fltd_messages = fltd_output.findall(
                "fdm:fltdMessage", namespaces=NAMESPACES
            )
            for fltd_message in fltd_messages:
                msg_type = fltd_message.get("msgType")
                parser = get_parser(msg_type)
                if parser:
                    parsed_message = parser(
                        etree.tostring(fltd_message, encoding="unicode")
                    )
                    if parsed_message:
                        parsed_data.append(parsed_message)
                else:
                    logger.warning(f"No parser registered for message type: {msg_type}")

        else:
            logger.warning("No known root element found in XML.")

        return parsed_data if parsed_data else None

    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_data[:500]}...")
        return None


def parse_and_store_to_database(xml_data: str):
    """Parses XML data and stores it to the database."""
    session = SessionLocal()
    try:
        logger.debug(xml_data)

        # Parse and store the XML data
        parsed_data = parse_xml_to_pydantic(xml_data)
        if parsed_data is not None:
            for data in parsed_data:
                msg_type = data.get("type")
                storer = get_storer(msg_type)
                if storer:
                    storer(session, data.get("data"))
                else:
                    logger.warning(f"No storer registered for message type: {msg_type}")
        else:
            logger.error("Failed to parse XML data.")
    except Exception as e:
        logger.error(f"Error parsing and storing XML data: {e}")
    finally:
        session.close()
