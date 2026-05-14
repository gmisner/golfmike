"""
Flight Plan Parser for Traffic Consumer
Parses flightPlanInformation messages from the traffic consumer (TFMS)
"""

from typing import List, Dict, Any
from lxml import etree
from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger
from utils.aircraft_id import normalize_aircraft_id


def parse_flight_plan_traffic(root: etree._Element) -> List[Dict[str, Any]]:
    """
    Parse flight plan messages from traffic consumer XML (pre-parsed root).

    Returns:
        List of parsed flight plan dictionaries
    """
    try:
        logger.debug("Root of flight plan XML parsed")

        # Find all fltdMessage elements
        messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
        logger.debug(f"Found {len(messages)} fltdMessage elements")

        parsed_data = []

        for message in messages:
            msg_type = message.get("msgType")
            aircraft_id_attr = message.get(
                "acid"
            )  # Get aircraft ID from attribute for logging
            logger.info(
                f"📋 Processing message type: {msg_type}, Aircraft: {aircraft_id_attr}"
            )

            # Process flight plan information messages
            if msg_type in [
                "flightPlanInformation",
                "FlightCreate",
                "HCS_FLIGHT_PLAN_MSG",
                "FD_FLIGHT_CREATE_MSG",
                "IADE_FLIGHT_PLAN_MSG",
                "flightPlanAmendmentInformation",
            ]:
                try:
                    # Initialize data with values from fltdMessage attributes (fallback)
                    aircraft_id = message.get("acid")
                    flight_ref = message.get("flightRef")
                    departure_airport = message.get("depArpt")
                    arrival_airport = message.get("arrArpt")
                    source_facility = message.get("sourceFacility")
                    source_timestamp = message.get("sourceTimeStamp")

                    # Try to get flight plan information element (nested structure)
                    flight_plan_elem = message.find(
                        "fdm:flightPlanInformation", namespaces=NAMESPACES
                    )
                    if flight_plan_elem is None:
                        # Try alternative location
                        flight_plan_elem = message.find(
                            ".//nxcm:flightPlanInformation", namespaces=NAMESPACES
                        )

                    gufi = None
                    igtd = None
                    aircraft_type = None
                    route_text = None

                    if flight_plan_elem is not None:
                        # Extract qualified aircraft ID
                        qualified_aircraft_id = flight_plan_elem.find(
                            "nxcm:qualifiedAircraftId", namespaces=NAMESPACES
                        )
                        if qualified_aircraft_id is not None:
                            # Extract aircraft ID (prefer nested over attribute)
                            aircraft_id_elem = qualified_aircraft_id.find(
                                "nxce:aircraftId", namespaces=NAMESPACES
                            )
                            if aircraft_id_elem is not None and aircraft_id_elem.text:
                                aircraft_id = aircraft_id_elem.text

                            # Extract GUFI
                            gufi_elem = qualified_aircraft_id.find(
                                "nxce:gufi", namespaces=NAMESPACES
                            )
                            if gufi_elem is not None and gufi_elem.text:
                                gufi = gufi_elem.text

                            # Extract flight reference (prefer nested over attribute)
                            flight_ref_elem = qualified_aircraft_id.find(
                                "nxce:flightReference", namespaces=NAMESPACES
                            )
                            if flight_ref_elem is not None and flight_ref_elem.text:
                                flight_ref = flight_ref_elem.text

                            # Extract times
                            igtd_elem = qualified_aircraft_id.find(
                                "nxce:igtd", namespaces=NAMESPACES
                            )
                            if igtd_elem is not None and igtd_elem.text:
                                igtd = igtd_elem.text

                        # Extract departure/arrival airports (prefer nested over attributes)
                        dep_point = flight_plan_elem.find(
                            ".//nxcm:departureLocation/nxce:locationIndicator",
                            namespaces=NAMESPACES,
                        )
                        if dep_point is not None and dep_point.text:
                            departure_airport = dep_point.text

                        arr_point = flight_plan_elem.find(
                            ".//nxcm:arrivalLocation/nxce:locationIndicator",
                            namespaces=NAMESPACES,
                        )
                        if arr_point is not None and arr_point.text:
                            arrival_airport = arr_point.text

                        # Extract aircraft type
                        aircraft_specs = flight_plan_elem.find(
                            "nxcm:flightAircraftSpecs", namespaces=NAMESPACES
                        )
                        if aircraft_specs is not None:
                            type_elem = aircraft_specs.find(
                                "nxce:aircraftType", namespaces=NAMESPACES
                            )
                            if type_elem is not None and type_elem.text:
                                aircraft_type = type_elem.text

                        # Extract route
                        route_elem = flight_plan_elem.find(
                            ".//nxcm:flightPlanRoute", namespaces=NAMESPACES
                        )
                        if route_elem is not None and route_elem.text:
                            route_text = route_elem.text
                    else:
                        # No nested structure, try to find GUFI elsewhere in the message
                        gufi_elem = message.find(".//nxce:gufi", namespaces=NAMESPACES)
                        if gufi_elem is not None and gufi_elem.text:
                            gufi = gufi_elem.text

                        # Try to find route in other locations
                        route_elem = message.find(
                            ".//nxcm:flightPlanRoute", namespaces=NAMESPACES
                        )
                        if route_elem is not None and route_elem.text:
                            route_text = route_elem.text

                        # Try to find aircraft type
                        aircraft_specs = message.find(
                            ".//nxcm:flightAircraftSpecs", namespaces=NAMESPACES
                        )
                        if aircraft_specs is not None:
                            type_elem = aircraft_specs.find(
                                "nxce:aircraftType", namespaces=NAMESPACES
                            )
                            if type_elem is not None and type_elem.text:
                                aircraft_type = type_elem.text

                    if not aircraft_id:
                        logger.warning(
                            "No aircraft_id found in flight plan message (neither in attributes nor nested elements)"
                        )
                        continue

                    flight_plan_data = {
                        "aircraft_id": normalize_aircraft_id(aircraft_id),
                        "gufi": gufi,
                        "flight_reference": flight_ref,
                        "departure_airport": departure_airport,
                        "arrival_airport": arrival_airport,
                        "igtd": igtd,
                        "aircraft_type": aircraft_type,
                        "route_text": route_text,
                        "source_facility": source_facility,
                        "source_timestamp": source_timestamp,
                        "status": "PLANNED",
                    }

                    parsed_data.append(flight_plan_data)
                    logger.info(
                        f"✅ Parsed flight plan: Aircraft={aircraft_id}, GUFI={gufi}, Ref={flight_ref}, Route={departure_airport}→{arrival_airport}"
                    )

                except Exception as e:
                    logger.error(
                        f"❌ Error parsing flight plan message (type: {msg_type}, aircraft: {aircraft_id_attr}): {e}",
                        exc_info=True,
                    )
                    continue
            else:
                # Log unhandled message types that might be flight plan related
                if msg_type and any(
                    keyword in msg_type.lower()
                    for keyword in ["flight", "plan", "create"]
                ):
                    logger.info(
                        f"⚠️ Unhandled flight-related message type: {msg_type} (Aircraft: {aircraft_id_attr})"
                    )

        logger.info(f"Parsed {len(parsed_data)} flight plan messages")
        return parsed_data

    except Exception as e:
        logger.error(f"Error parsing flight plan XML: {e}", exc_info=True)
        return []
