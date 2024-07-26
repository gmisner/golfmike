from typing import List
from lxml import etree
from models.pydantic.track_information import TrackInformationModel
from utils.logger import main_logger as logger

NAMESPACES = {
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
}


def convert_dms_to_decimal(
    degrees: str, minutes: str, seconds: str, direction: str
) -> str:
    if degrees is None or minutes is None or seconds is None or direction is None:
        logger.debug("Degrees, minutes, or seconds are None")
        return None
    try:
        decimal = int(degrees) + int(minutes) / 60 + int(seconds) / 3600
        if direction in ["SOUTH", "WEST"]:
            decimal = -decimal
        return f"{decimal:.5f}"
    except ValueError as e:
        logger.error(f"Error converting DMS to decimal: {e}")
        return None


def parse_track_information(xml_data: str) -> List[TrackInformationModel]:
    try:
        root = etree.fromstring(xml_data)
        logger.debug("Root of trackInformation XML parsed")

        messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
        logger.debug(f"Found {len(messages)} fltdMessage elements")
        parsed_data = []

        for message in messages:
            msg_type = message.get("msgType")
            logger.debug(f"Processing message type: {msg_type}")

            if msg_type == "trackInformation":
                try:
                    track_info = message.find(
                        "fdm:trackInformation", namespaces=NAMESPACES
                    )
                    if track_info is None:
                        logger.warning("trackInformation element is missing")
                        continue

                    qualified_aircraft_id = track_info.find(
                        "nxcm:qualifiedAircraftId", namespaces=NAMESPACES
                    )
                    if qualified_aircraft_id is None:
                        logger.warning("qualifiedAircraftId element is missing")
                        continue

                    position = track_info.find("nxcm:position", namespaces=NAMESPACES)
                    reported_altitude = track_info.find(
                        "nxcm:reportedAltitude", namespaces=NAMESPACES
                    )

                    latitude = None
                    longitude = None
                    if position is not None:
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
                        altitude_elem = reported_altitude.find(
                            "nxce:assignedAltitude/nxce:simpleAltitude",
                            namespaces=NAMESPACES,
                        )
                        altitude_str = (
                            altitude_elem.text if altitude_elem is not None else None
                        )
                        if altitude_str:
                            try:
                                altitude = int(altitude_str.replace("C", ""))
                            except ValueError:
                                logger.error(f"Invalid altitude value: {altitude_str}")

                    speed_elem = track_info.find("nxcm:speed", namespaces=NAMESPACES)
                    speed = int(speed_elem.text) if speed_elem is not None else None

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
                        "user_category": qualified_aircraft_id.get("userCategory", ""),
                        "latitude": latitude if latitude is not None else "",
                        "longitude": longitude if longitude is not None else "",
                    }
                    parsed_model = TrackInformationModel(**data)
                    logger.debug(f"Parsed model: {parsed_model}")
                    parsed_data.append(parsed_model)
                except Exception as e:
                    logger.error(
                        f"Error parsing trackInformation element: {e}", exc_info=True
                    )

        logger.debug(f"Total parsed trackInformation elements: {len(parsed_data)}")
        return parsed_data

    except Exception as e:
        logger.error(f"Error parsing trackInformation: {e}", exc_info=True)
        logger.error(f"Problematic XML (excerpt): {xml_data[:500]}")
        return []
