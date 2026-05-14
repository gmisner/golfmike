"""
Flight Plan XML Parser for Solace Queue Data
Parses flight plan XML data from the FDPS Solace queue
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger

try:
    from dateutil.parser import isoparse as _isoparse
    _HAS_DATEUTIL = True
except ImportError:
    _HAS_DATEUTIL = False


class FlightPlanXMLParser:
    """Parser for flight plan XML data from Solace queues"""

    def __init__(self):
        self.logger = logger

    def parse_flight_plan_xml(self, xml_data: str) -> Optional[Dict[str, Any]]:
        """
        Parse flight plan XML data and extract relevant information

        Args:
            xml_data: Raw XML string from Solace queue

        Returns:
            Dictionary containing parsed flight plan data or None if parsing fails
        """
        try:
            root = ET.fromstring(xml_data)
            self.logger.debug(f"Parsing flight plan XML with root tag: {root.tag}")

            # Initialize result dictionary
            flight_plan_data = {
                "aircraft_id": None,
                "gufi": None,
                "flight_reference": None,
                "departure_airport": None,
                "arrival_airport": None,
                "departure_time": None,
                "arrival_time": None,
                "aircraft_type": None,
                "aircraft_operator": None,
                "route_text": None,
                "filed_route": None,
                "status": "PLANNED",
                "source_facility": None,
                "source_timestamp": None,
                "flight_plan_data": xml_data,
            }

            # Simple approach: iterate through all elements and extract what we need
            current_context = None
            found_tags = set()
            for elem in root.iter():
                tag = elem.tag
                text = elem.text.strip() if elem.text else ""
                found_tags.add(tag)

                # Track context for aerodrome elements
                if tag.endswith("departureLocation"):
                    current_context = "departure"
                elif tag.endswith("arrivalLocation"):
                    current_context = "arrival"

                if not text:
                    continue

                # Extract aircraft ID
                if tag.endswith("aircraftId"):
                    flight_plan_data["aircraft_id"] = normalize_aircraft_id(text)

                # Extract GUFI
                elif tag.endswith("gufi"):
                    flight_plan_data["gufi"] = text

                # Extract flight reference
                elif tag.endswith("flightReference") or tag.endswith("flightNumber"):
                    flight_plan_data["flight_reference"] = text

                # Extract departure/arrival airport
                elif tag.endswith("locationIndicator"):
                    if current_context == "departure":
                        flight_plan_data["departure_airport"] = text.upper()
                    elif current_context == "arrival":
                        flight_plan_data["arrival_airport"] = text.upper()

                # Extract departure time
                elif tag.endswith("departureTime") or tag.endswith("igtd"):
                    flight_plan_data["departure_time"] = self._parse_datetime(text)

                # Extract arrival time
                elif tag.endswith("arrivalTime") or tag.endswith("iata"):
                    flight_plan_data["arrival_time"] = self._parse_datetime(text)

                # Extract aircraft type
                elif tag.endswith("aircraftType") or tag.endswith("aircraftModel"):
                    flight_plan_data["aircraft_type"] = text

                # Extract operator
                elif tag.endswith("operator") or tag.endswith("airline"):
                    flight_plan_data["aircraft_operator"] = text

                # Extract route
                elif tag.endswith("route") or tag.endswith("routeText"):
                    flight_plan_data["route_text"] = text

                # Extract status
                elif tag.endswith("status") or tag.endswith("flightStatus"):
                    flight_plan_data["status"] = text.upper()

                # Extract source facility
                elif tag.endswith("sourceFacility") or tag.endswith("facility"):
                    flight_plan_data["source_facility"] = text

                # Extract timestamp
                elif tag.endswith("timestamp") or tag.endswith("timeStamp"):
                    flight_plan_data["source_timestamp"] = self._parse_datetime(text)

            # Log successful parsing
            self.logger.info(
                f"Successfully parsed flight plan for aircraft: {flight_plan_data['aircraft_id']}"
            )
            self.logger.debug(f"Flight plan data: {flight_plan_data}")
            self.logger.debug(f"Found tags: {sorted(found_tags)}")

            return flight_plan_data

        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing flight plan XML: {e}", exc_info=True)
            return None

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string, always returning a UTC-aware datetime."""
        if not datetime_str:
            return None

        s = datetime_str.strip()

        # Prefer dateutil — handles Z suffix, offsets, and most ISO variants
        if _HAS_DATEUTIL:
            try:
                dt = _isoparse(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, OverflowError):
                pass

        # Fallback strptime; all naive results are treated as UTC
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        self.logger.warning(f"Could not parse datetime: {datetime_str!r}")
        return None


# Function interface for backward compatibility
def parse_flight_plan(xml_data) -> Optional[Dict[str, Any]]:
    """
    Parse flight plan XML data - function interface for backward compatibility
    Handles both bytes and string input (for traffic consumer compatibility)

    Args:
        xml_data: Raw XML string or bytes from Solace queue

    Returns:
        Dictionary containing parsed flight plan data or None if parsing fails
    """
    # Convert bytes to string if needed
    if isinstance(xml_data, bytes):
        xml_data = xml_data.decode("utf-8")

    parser = FlightPlanXMLParser()
    result = parser.parse_flight_plan_xml(xml_data)

    # Return as list for consistency with other parsers
    if result:
        return [result]
    return []
