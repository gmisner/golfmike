from typing import List
from lxml import etree
from models.pydantic.track_information import TrackInformationModel
from utils.logger import main_logger as logger

# Define namespaces to parse the XML document correctly
NAMESPACES = {
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
}


# Function to convert DMS (Degrees, Minutes, Seconds) format to Decimal format
def convert_dms_to_decimal(
    degrees: str, minutes: str, seconds: str, direction: str
) -> str:
    # Ensure all components are provided before converting
    if degrees is None or minutes is None or seconds is None or direction is None:
        logger.debug("Degrees, minutes, or seconds are None")
        return None
    try:
        # Calculate decimal value from DMS
        decimal = int(degrees) + int(minutes) / 60 + int(seconds) / 3600
        # Adjust sign based on direction (SOUTH or WEST should be negative)
        if direction in ["SOUTH", "WEST"]:
            decimal = -decimal
        logger.debug(f"Converted DMS to decimal: {decimal}")
        return f"{decimal:.5f}"
    except ValueError as e:
        # Log any conversion error
        logger.error(f"Error converting DMS to decimal: {e}")
        return None


# Function to parse track information from XML data
def parse_track_information(xml_data: str) -> List[TrackInformationModel]:
    try:
        logger.debug("Starting to parse trackInformation XML")
        # Parse the XML data into an ElementTree object
        root = etree.fromstring(xml_data)
        logger.debug("Root of trackInformation XML parsed")

        # Find all flight message elements in the XML
        messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
        logger.debug(f"Found {len(messages)} fltdMessage elements")
        parsed_data = []

        # Iterate through each flight message
        for message in messages:
            msg_type = message.get("msgType")
            logger.debug(f"Processing message type: {msg_type}")

            # Only process messages of type "trackInformation"
            if msg_type == "trackInformation":
                try:
                    # Find the trackInformation element
                    track_info = message.find(
                        "fdm:trackInformation", namespaces=NAMESPACES
                    )
                    if track_info is None:
                        logger.warning("trackInformation element is missing")
                        continue

                    # Extract qualified aircraft identification information
                    qualified_aircraft_id = track_info.find(
                        "nxcm:qualifiedAircraftId", namespaces=NAMESPACES
                    )
                    if qualified_aircraft_id is None:
                        logger.warning("qualifiedAircraftId element is missing")
                        continue

                    # Extract user category (e.g., COMMERCIAL, PRIVATE)
                    user_category = qualified_aircraft_id.get("userCategory", "")
                    logger.debug(f"User category: {user_category}")

                    # Extract position and altitude information
                    position = track_info.find("nxcm:position", namespaces=NAMESPACES)
                    reported_altitude = track_info.find(
                        "nxcm:reportedAltitude", namespaces=NAMESPACES
                    )

                    latitude = None
                    longitude = None
                    if position is not None:
                        # Extract latitude and longitude in DMS format and convert to decimal
                        latitude_elem = position.find(
                            "nxce:latitude/nxce:latitudeDMS", namespaces=NAMESPACES
                        )
                        longitude_elem = position.find(
                            "nxce:longitude/nxce:longitudeDMS", namespaces=NAMESPACES
                        )

                        if latitude_elem is not None and longitude_elem is not None:
                            latitude = convert_dms_to_decimal(
                                latitude_elem.get("degrees"),
                                latitude_elem.get("minutes"),
                                latitude_elem.get("seconds"),
                                latitude_elem.get("direction"),
                            )
                            longitude = convert_dms_to_decimal(
                                longitude_elem.get("degrees"),
                                longitude_elem.get("minutes"),
                                longitude_elem.get("seconds"),
                                longitude_elem.get("direction"),
                            )
                        logger.debug(f"Latitude: {latitude}, Longitude: {longitude}")

                    altitude = None
                    if reported_altitude is not None:
                        # Extract assigned altitude value
                        altitude_elem = reported_altitude.find(
                            "nxce:assignedAltitude/nxce:simpleAltitude",
                            namespaces=NAMESPACES,
                        )
                        altitude_str = (
                            altitude_elem.text if altitude_elem is not None else None
                        )
                        if altitude_str:
                            try:
                                # Convert altitude to integer
                                altitude = int(altitude_str.replace("C", ""))
                                logger.debug(f"Altitude: {altitude}")
                            except ValueError:
                                logger.error(f"Invalid altitude value: {altitude_str}")

                    # Extract speed information
                    speed_elem = track_info.find("nxcm:speed", namespaces=NAMESPACES)
                    speed = int(speed_elem.text) if speed_elem is not None else None
                    logger.debug(f"Speed: {speed}")

                    # Extract additional route and flight data elements
                    etd_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:etd", namespaces=NAMESPACES
                    )
                    eta_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:eta", namespaces=NAMESPACES
                    )
                    diversion_indicator_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:diversionIndicator",
                        namespaces=NAMESPACES,
                    )
                    rvsm_data_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:rvsmData", namespaces=NAMESPACES
                    )
                    next_position_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:nextPosition", namespaces=NAMESPACES
                    )
                    flight_traversal_data_elem = track_info.findall(
                        "nxcm:ncsmRouteData/nxcm:flightTraversalData2/nxce:fix",
                        namespaces=NAMESPACES,
                    )
                    waypoint_elems = track_info.findall(
                        "nxcm:ncsmRouteData/nxcm:flightTraversalData2/nxce:waypoint",
                        namespaces=NAMESPACES,
                    )
                    sector_elems = track_info.findall(
                        "nxcm:ncsmRouteData/nxcm:sector", namespaces=NAMESPACES
                    )
                    route_of_flight_elem = track_info.find(
                        "nxcm:ncsmRouteData/nxcm:routeOfFlight", namespaces=NAMESPACES
                    )

                    # Extract fixes, waypoints, and sectors
                    fixes = (
                        [fix.text for fix in flight_traversal_data_elem]
                        if flight_traversal_data_elem
                        else []
                    )
                    logger.debug(f"Fixes: {fixes}")
                    waypoints = (
                        [
                            {
                                "latitude": waypoint.get("latitudeDecimal"),
                                "longitude": waypoint.get("longitudeDecimal"),
                                "elapsed_time": waypoint.get("elapsedTime"),
                            }
                            for waypoint in waypoint_elems
                        ]
                        if waypoint_elems
                        else []
                    )
                    logger.debug(f"Waypoints: {waypoints}")
                    sectors = (
                        [sector.text for sector in sector_elems] if sector_elems else []
                    )
                    logger.debug(f"Sectors: {sectors}")

                    # Collect all parsed data into a dictionary
                    data = {
                        "aircraft_id": (
                            qualified_aircraft_id.find(
                                "nxce:aircraftId", namespaces=NAMESPACES
                            ).text
                            if qualified_aircraft_id.find(
                                "nxce:aircraftId", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        "gufi": (
                            qualified_aircraft_id.find(
                                "nxce:gufi", namespaces=NAMESPACES
                            ).text
                            if qualified_aircraft_id.find(
                                "nxce:gufi", namespaces=NAMESPACES
                            )
                            is not None
                            else ""
                        ),
                        "igtd": (
                            qualified_aircraft_id.find(
                                "nxce:igtd", namespaces=NAMESPACES
                            ).text
                            if qualified_aircraft_id.find(
                                "nxce:igtd", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        "departure_airport": (
                            qualified_aircraft_id.find(
                                "nxce:departurePoint/nxce:airport",
                                namespaces=NAMESPACES,
                            ).text
                            if qualified_aircraft_id.find(
                                "nxce:departurePoint/nxce:airport",
                                namespaces=NAMESPACES,
                            )
                            is not None
                            else ""
                        ),
                        "arrival_airport": (
                            qualified_aircraft_id.find(
                                "nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES
                            ).text
                            if qualified_aircraft_id.find(
                                "nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES
                            )
                            is not None
                            else ""
                        ),
                        "speed": speed,
                        "altitude": altitude if altitude is not None else 0,
                        "time_at_position": (
                            track_info.find(
                                "nxcm:timeAtPosition", namespaces=NAMESPACES
                            ).text
                            if track_info.find(
                                "nxcm:timeAtPosition", namespaces=NAMESPACES
                            )
                            is not None
                            else None
                        ),
                        "airline": message.get("airline", ""),
                        "aircraft_category": qualified_aircraft_id.get(
                            "aircraftCategory", ""
                        ),
                        "user_category": user_category,
                        "latitude": latitude if latitude is not None else "",
                        "longitude": longitude if longitude is not None else "",
                        "etd": (
                            etd_elem.get("timeValue") if etd_elem is not None else None
                        ),
                        "eta": (
                            eta_elem.get("timeValue") if eta_elem is not None else None
                        ),
                        "diversion_indicator": (
                            diversion_indicator_elem.text
                            if diversion_indicator_elem is not None
                            else None
                        ),
                        "rvsm_data": (
                            rvsm_data_elem.attrib
                            if rvsm_data_elem is not None
                            else None
                        ),
                        "next_position": (
                            {
                                "latitude": next_position_elem.get("latitudeDecimal"),
                                "longitude": next_position_elem.get("longitudeDecimal"),
                            }
                            if next_position_elem is not None
                            else None
                        ),
                        "fixes": fixes,
                        "waypoints": waypoints,
                        "sectors": sectors,
                        "route_of_flight": (
                            route_of_flight_elem.text
                            if route_of_flight_elem is not None
                            else None
                        ),
                    }

                    # Create an instance of TrackInformationModel with the parsed data
                    parsed_model = TrackInformationModel(**data)
                    logger.debug(f"Parsed model: {parsed_model}")
                    # Append the parsed model to the list of parsed data
                    parsed_data.append(parsed_model)
                except Exception as e:
                    # Log any exception that occurs while parsing a trackInformation element
                    logger.error(
                        f"Error parsing trackInformation element: {e}", exc_info=True
                    )

        logger.debug(f"Total parsed trackInformation elements: {len(parsed_data)}")
        return parsed_data

    except Exception as e:
        # Log any exception that occurs during the entire parsing process
        logger.error(f"Error parsing trackInformation: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_data[:500]}")
        return []
