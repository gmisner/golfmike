# swim_data_processor.py
from lxml import etree
from parser_storer_registry import get_parser, get_storer
from typing import Union, Tuple
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError
from db_config import SessionLocal  # Import SessionLocal
from error_handling import (
    retry_with_backoff,
    handle_database_errors,
    track_errors,
    db_circuit_breaker,
)

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


def parse_xml_to_pydantic(xml_string: str) -> Union[Tuple[str, list], None]:
    try:
        # Convert the XML string to bytes once
        xml_bytes = xml_string.encode("utf-8")
        logger.debug("Converting XML string to bytes.")

        # Parse the XML with optimized parser
        parser = etree.XMLParser(recover=True, huge_tree=True)
        root = etree.fromstring(xml_bytes, parser=parser)
        logger.debug("Root of XML parsed successfully.")

        # Extract message type from XML with error handling
        msg_type_elements = root.xpath("//@msgType", namespaces=NAMESPACES)
        if not msg_type_elements:
            logger.error("No msgType attribute found in XML")
            return None

        msg_type = msg_type_elements[0]
        logger.debug(f"Extracted message type: {msg_type}")

        # Get the appropriate parser function based on message type
        parser_func = get_parser(msg_type)
        if not parser_func:
            logger.error(f"No parser registered for message type: {msg_type}")
            return None

        logger.debug(f"Using parser function: {parser_func}")
        parsed_data = parser_func(xml_bytes)
        logger.debug(f"Parsed data successfully for message type: {msg_type}")
        return msg_type, parsed_data

    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error: {e}")
        logger.error(f"Problematic XML (excerpt): {xml_string[:500]}")
        return None
    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_string[:500]}")
        return None


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
@handle_database_errors
@track_errors("database_operation")
def parse_and_store_to_database(xml_string: str) -> bool:
    logger.debug("Starting parse_and_store_to_database function.")
    session = None
    try:
        # Parse XML first to avoid unnecessary database connection
        parsed_data = parse_xml_to_pydantic(xml_string)
        if parsed_data is None:
            logger.error("Failed to parse XML data.")
            return False

        msg_type, data = parsed_data
        logger.debug(f"Parsed data for message type: {msg_type}")

        # Get the appropriate storer function based on message type
        storer_func = get_storer(msg_type)
        if not storer_func:
            logger.error(f"No storer registered for message type: {msg_type}")
            return False

        # Use circuit breaker for database operations
        def _store_data():
            nonlocal session
            session = SessionLocal()
            logger.debug("Database session created.")

            # Pass the session and data to the storer function
            logger.debug("Storing data to database.")
            storer_func(data, session=session)
            session.commit()
            logger.info(f"Stored data successfully for message type: {msg_type}")
            return True

        return db_circuit_breaker.call(_store_data)

    except Exception as e:
        logger.error(
            f"Unexpected error occurred during parse_and_store_to_database: {e}",
            exc_info=True,
        )
        return False
    finally:
        if session:
            session.close()
        logger.debug("Finished parse_and_store_to_database function.")
