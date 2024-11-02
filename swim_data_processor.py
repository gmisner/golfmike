# swim_data_processor.py
from lxml import etree
from parser_storer_registry import get_parser, get_storer
from typing import Union, Tuple
from utils.logger import main_logger as logger
from sqlalchemy.exc import SQLAlchemyError
from db_config import SessionLocal  # Import SessionLocal

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
        # Convert the XML string to bytes
        logger.debug("Converting XML string to bytes.")
        xml_bytes = xml_string.encode("utf-8")

        # Parse the XML
        root = etree.fromstring(xml_bytes)
        logger.debug("Root of XML parsed successfully.")

        # Extract message type from XML
        msg_type = root.xpath("//@msgType", namespaces=NAMESPACES)[0]
        logger.debug(f"Extracted message type: {msg_type}")

        # Get the appropriate parser function based on message type
        parser_func = get_parser(msg_type)
        if parser_func:
            logger.debug(f"Using parser function: {parser_func}")
            parsed_data = parser_func(xml_bytes)
            logger.debug(f"Parsed data successfully for message type: {msg_type}")
            return msg_type, parsed_data
        else:
            logger.error(f"No parser registered for message type: {msg_type}")
            return None
    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_string[:500]}")
        return None


def parse_and_store_to_database(xml_string: str) -> bool:
    logger.info("Starting parse_and_store_to_database function.")
    try:
        with SessionLocal() as session:  # Open session using SessionLocal
            logger.info("Database session created.")
            parsed_data = parse_xml_to_pydantic(xml_string)
            if parsed_data is not None:
                msg_type, data = parsed_data
                logger.debug(f"Parsed data for message type: {msg_type}")

                # Get the appropriate storer function based on message type
                storer_func = get_storer(msg_type)
                if storer_func:
                    logger.debug(f"Using storer function: {storer_func}")
                    try:
                        # Pass the session and data to the storer function
                        logger.debug("Storing data to database.")
                        storer_func(data, session=session)  # Corrected argument order
                        session.commit()  # Commit after storer_func completes
                        logger.info(
                            f"Stored data successfully for message type: {msg_type}"
                        )
                        return True
                    except SQLAlchemyError as e:
                        # Rollback the session in case of an error
                        session.rollback()
                        logger.error(
                            f"SQLAlchemy error while committing data: {e}",
                            exc_info=True,
                        )
                        return False
                else:
                    logger.error(f"No storer registered for message type: {msg_type}")
                    return False
            else:
                logger.error("Failed to parse XML data.")
                return False
    except Exception as e:
        logger.error(
            f"Unexpected error occurred during parse_and_store_to_database: {e}",
            exc_info=True,
        )
        return False
    finally:
        logger.info("Finished parse_and_store_to_database function.")
