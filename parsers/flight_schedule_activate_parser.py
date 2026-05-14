"""
FlightScheduleActivate XML Parser
Parses FlightScheduleActivate XML messages to extract route assignment data
"""

from typing import List, Dict, Any
from lxml import etree
from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from parsers.ncsm_route_info_body import (
    extract_route_assignment_from_ncsm_route_info_body,
)
from utils.logger import main_logger as logger


def parse_flight_schedule_activate(root: etree._Element) -> List[Dict[str, Any]]:
    """
    Parse FlightScheduleActivate XML from an already-parsed root.

    Returns:
        List of dictionaries containing parsed route assignment data
    """
    try:
        logger.debug("Starting to parse FlightScheduleActivate XML")

        messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
        logger.debug(f"Found {len(messages)} fltdMessage elements")

        parsed_data: List[Dict[str, Any]] = []

        for message in messages:
            msg_type = message.get("msgType")
            logger.debug(f"Processing message type: {msg_type}")

            if msg_type == "FlightScheduleActivate":
                try:
                    schedule_activate = message.find(
                        "fdm:ncsmFlightScheduleActivate", namespaces=NAMESPACES
                    )
                    if schedule_activate is None:
                        logger.warning("ncsmFlightScheduleActivate element is missing")
                        continue
                    data = extract_route_assignment_from_ncsm_route_info_body(
                        schedule_activate, message
                    )
                    if data:
                        logger.debug("Parsed FlightScheduleActivate data: {}", data)
                        parsed_data.append(data)
                except Exception as e:
                    logger.error(
                        f"Error parsing FlightScheduleActivate element: {e}",
                        exc_info=True,
                    )

        logger.debug(
            f"Total parsed FlightScheduleActivate elements: {len(parsed_data)}"
        )
        return parsed_data

    except Exception as e:
        logger.error(f"Error parsing FlightScheduleActivate: {e}", exc_info=True)
        try:
            excerpt = etree.tostring(root, encoding="unicode")[:500]
        except Exception:
            excerpt = "(could not serialize root)"
        logger.error(f"Problematic XML (excerpt): {excerpt}")
        return []
