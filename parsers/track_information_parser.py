from typing import List
from lxml import etree
from models.pydantic.track_information import TrackInformationModel
from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger
from utils.aircraft_id import normalize_aircraft_id
from utils.nas_altitude import simple_altitude_hundreds_to_feet


def _sort_by_sequence(elems: List[etree._Element]) -> List[etree._Element]:
    """Sort TFM elements that carry sequenceNumber (fixes, sectors, waypoints, etc.)."""

    def seq_key(el: etree._Element) -> int:
        s = el.get("sequenceNumber")
        try:
            return int(s) if s is not None else 0
        except ValueError:
            return 0

    return sorted(elems, key=seq_key)


def _direction_is_negative(direction: str) -> bool:
    """NAS/FIXM may use full words or single-letter compass directions."""
    if not direction:
        return False
    d = direction.strip().upper()
    return d in ("S", "SOUTH", "W", "WEST")


# Function to convert DMS (Degrees, Minutes, Seconds) format to Decimal format
def convert_dms_to_decimal(
    degrees: str, minutes: str, seconds: str, direction: str
) -> str:
    # Degrees, minutes, and direction are required; seconds is often omitted in TFM XML
    if degrees is None or minutes is None or direction is None:
        logger.debug("DMS degrees, minutes, or direction is None")
        return None
    if seconds is None or seconds == "":
        seconds = "0"
    try:
        # Use float so fractional minutes/seconds (e.g. "30.5") and leading zeros work
        d = float(str(degrees).strip())
        m = float(str(minutes).strip())
        s = float(str(seconds).strip())
        decimal = d + m / 60.0 + s / 3600.0
        if _direction_is_negative(direction):
            decimal = -decimal
        logger.debug("Converted DMS to decimal: {}", decimal)
        return f"{decimal:.8f}".rstrip("0").rstrip(".")
    except ValueError as e:
        logger.error(f"Error converting DMS to decimal: {e}")
        return None


def parse_track_information(root: etree._Element) -> List[TrackInformationModel]:
    try:
        logger.debug("Starting to parse trackInformation XML")

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
                        lat_wrap = position.find("nxce:latitude", namespaces=NAMESPACES)
                        lon_wrap = position.find(
                            "nxce:longitude", namespaces=NAMESPACES
                        )

                        # Prefer decimal degrees on position (authoritative when present)
                        if lat_wrap is not None and lon_wrap is not None:
                            lat_dec = lat_wrap.get("latitudeDecimal")
                            lon_dec = lon_wrap.get("longitudeDecimal")
                            if lat_dec and lon_dec:
                                latitude = str(lat_dec).strip()
                                longitude = str(lon_dec).strip()

                        # DMS under nxce:latitude / nxce:longitude
                        if latitude is None or longitude is None:
                            latitude_elem = position.find(
                                "nxce:latitude/nxce:latitudeDMS", namespaces=NAMESPACES
                            )
                            longitude_elem = position.find(
                                "nxce:longitude/nxce:longitudeDMS",
                                namespaces=NAMESPACES,
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

                        # Do not use ncsmTrackData/nextEvent here: that point is the *next* fix on
                        # the route, not the aircraft's current position (would appear "off" on a map).
                        logger.debug("Latitude: {}, Longitude: {}", latitude, longitude)

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
                                # NAS simpleAltitude is flight level in hundreds of feet (360 = FL360 = 36000 ft)
                                raw_fl = int(altitude_str.replace("C", ""))
                                altitude = simple_altitude_hundreds_to_feet(raw_fl)
                                logger.debug(f"Altitude (ft): {altitude} (FL{raw_fl})")
                            except ValueError:
                                logger.error(f"Invalid altitude value: {altitude_str}")

                    # Extract speed information
                    speed_elem = track_info.find("nxcm:speed", namespaces=NAMESPACES)
                    speed = int(speed_elem.text) if speed_elem is not None else None
                    logger.debug(f"Speed: {speed}")

                    # Route / traversal (fixes, waypoints, sectors, airways, centers live under flightTraversalData2)
                    route_data_root = track_info.find(
                        "nxcm:ncsmRouteData", namespaces=NAMESPACES
                    )
                    etd_elem = (
                        route_data_root.find("nxcm:etd", namespaces=NAMESPACES)
                        if route_data_root is not None
                        else None
                    )
                    eta_elem = (
                        route_data_root.find("nxcm:eta", namespaces=NAMESPACES)
                        if route_data_root is not None
                        else None
                    )
                    diversion_indicator_elem = (
                        route_data_root.find(
                            "nxcm:diversionIndicator", namespaces=NAMESPACES
                        )
                        if route_data_root is not None
                        else None
                    )
                    rvsm_data_elem = (
                        route_data_root.find("nxcm:rvsmData", namespaces=NAMESPACES)
                        if route_data_root is not None
                        else None
                    )
                    next_position_elem = (
                        route_data_root.find("nxcm:nextPosition", namespaces=NAMESPACES)
                        if route_data_root is not None
                        else None
                    )
                    route_of_flight_elem = (
                        route_data_root.find(
                            "nxcm:routeOfFlight", namespaces=NAMESPACES
                        )
                        if route_data_root is not None
                        else None
                    )

                    star_elem = (
                        route_data_root.find("nxcm:star", namespaces=NAMESPACES)
                        if route_data_root is not None
                        else None
                    )
                    star_transition_elem = (
                        route_data_root.find(
                            "nxcm:starTransitionFix", namespaces=NAMESPACES
                        )
                        if route_data_root is not None
                        else None
                    )
                    route_arrival_elem = (
                        route_data_root.find(
                            "nxcm:arrivalFixAndTime", namespaces=NAMESPACES
                        )
                        if route_data_root is not None
                        else None
                    )

                    traversal = (
                        route_data_root.find(
                            "nxcm:flightTraversalData2", namespaces=NAMESPACES
                        )
                        if route_data_root is not None
                        else None
                    )
                    fix_elems = (
                        _sort_by_sequence(
                            traversal.findall("nxce:fix", namespaces=NAMESPACES)
                        )
                        if traversal is not None
                        else []
                    )
                    waypoint_elems = (
                        _sort_by_sequence(
                            traversal.findall("nxce:waypoint", namespaces=NAMESPACES)
                        )
                        if traversal is not None
                        else []
                    )
                    sector_elems = (
                        _sort_by_sequence(
                            traversal.findall("nxce:sector", namespaces=NAMESPACES)
                        )
                        if traversal is not None
                        else []
                    )
                    airway_elems = (
                        _sort_by_sequence(
                            traversal.findall("nxce:airway", namespaces=NAMESPACES)
                        )
                        if traversal is not None
                        else []
                    )
                    center_elems = (
                        _sort_by_sequence(
                            traversal.findall("nxce:center", namespaces=NAMESPACES)
                        )
                        if traversal is not None
                        else []
                    )

                    # Extract ncsmTrackData (track data with fixes and times)
                    ncsm_track_data_elem = track_info.find(
                        "nxcm:ncsmTrackData", namespaces=NAMESPACES
                    )

                    track_data = None
                    if ncsm_track_data_elem is not None:
                        # Extract departure fix and time
                        departure_fix_elem = ncsm_track_data_elem.find(
                            "nxcm:departureFixAndTime", namespaces=NAMESPACES
                        )
                        departure_fix = None
                        if departure_fix_elem is not None:
                            departure_fix = {
                                "fix_name": departure_fix_elem.get("fixName"),
                                "arr_time": departure_fix_elem.get("arrTime"),
                            }

                        # Extract arrival fix and time
                        arrival_fix_elem = ncsm_track_data_elem.find(
                            "nxcm:arrivalFixAndTime", namespaces=NAMESPACES
                        )
                        arrival_fix = None
                        if arrival_fix_elem is not None:
                            arrival_fix = {
                                "fix_name": arrival_fix_elem.get("fixName"),
                                "arr_time": arrival_fix_elem.get("arrTime"),
                            }

                        # Extract next event
                        next_event_elem = ncsm_track_data_elem.find(
                            "nxcm:nextEvent", namespaces=NAMESPACES
                        )
                        next_event = None
                        if next_event_elem is not None:
                            next_event = {
                                "latitude": next_event_elem.get("latitudeDecimal"),
                                "longitude": next_event_elem.get("longitudeDecimal"),
                            }

                        # Extract ETA from track data
                        track_eta_elem = ncsm_track_data_elem.find(
                            "nxcm:eta", namespaces=NAMESPACES
                        )
                        track_eta = None
                        if track_eta_elem is not None:
                            track_eta = {
                                "eta_type": track_eta_elem.get("etaType"),
                                "time_value": track_eta_elem.get("timeValue"),
                            }

                        # Extract RVSM data from track data
                        track_rvsm_elem = ncsm_track_data_elem.find(
                            "nxcm:rvsmData", namespaces=NAMESPACES
                        )
                        track_rvsm = None
                        if track_rvsm_elem is not None:
                            # lxml attrib is _Attrib — must be plain dict for JSON
                            track_rvsm = dict(track_rvsm_elem.attrib)

                        track_data = {
                            "departure_fix": departure_fix,
                            "arrival_fix": arrival_fix,
                            "next_event": next_event,
                            "eta": track_eta,
                            "rvsm_data": track_rvsm,
                        }
                        logger.debug(f"Extracted track data: {track_data}")

                    fixes = [f.text.strip() for f in fix_elems if f.text]
                    logger.debug(f"Fixes: {fixes}")
                    waypoints = [
                        {
                            "latitude": w.get("latitudeDecimal"),
                            "longitude": w.get("longitudeDecimal"),
                            "elapsed_time": w.get("elapsedTime"),
                            "sequence_number": w.get("sequenceNumber"),
                        }
                        for w in waypoint_elems
                    ]
                    logger.debug(f"Waypoints: {waypoints}")
                    sector_details = [
                        {
                            "name": s.text.strip() if s.text else "",
                            "sequence_number": s.get("sequenceNumber"),
                            "elapsed_entry_time": s.get("elapsedEntryTime"),
                        }
                        for s in sector_elems
                    ]
                    sectors = [d["name"] for d in sector_details if d.get("name")]
                    logger.debug(f"Sectors: {sectors}")
                    airways = [a.text.strip() for a in airway_elems if a.text]
                    centers = [
                        {
                            "name": c.text.strip() if c.text else "",
                            "sequence_number": c.get("sequenceNumber"),
                            "elapsed_entry_time": c.get("elapsedEntryTime"),
                        }
                        for c in center_elems
                    ]

                    cid_el = qualified_aircraft_id.find(
                        "nxce:computerId", namespaces=NAMESPACES
                    )
                    computer_facility = None
                    computer_id_number = None
                    if cid_el is not None:
                        fi = cid_el.find(
                            "nxce:facilityIdentifier", namespaces=NAMESPACES
                        )
                        idn = cid_el.find("nxce:idNumber", namespaces=NAMESPACES)
                        computer_facility = (
                            fi.text.strip() if fi is not None and fi.text else None
                        )
                        computer_id_number = (
                            idn.text.strip() if idn is not None and idn.text else None
                        )

                    # Collect all parsed data into a dictionary
                    _aid_el = qualified_aircraft_id.find(
                        "nxce:aircraftId", namespaces=NAMESPACES
                    )
                    _aid_raw = (
                        _aid_el.text.strip()
                        if _aid_el is not None and _aid_el.text
                        else None
                    )
                    data = {
                        "aircraft_id": normalize_aircraft_id(_aid_raw),
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
                        "flight_ref": message.get("flightRef"),
                        "source_facility": message.get("sourceFacility"),
                        "source_time_stamp": message.get("sourceTimeStamp"),
                        "aircraft_category": qualified_aircraft_id.get(
                            "aircraftCategory", ""
                        ),
                        "user_category": user_category,
                        "computer_facility": computer_facility,
                        "computer_id_number": computer_id_number,
                        "latitude": latitude if latitude is not None else None,
                        "longitude": longitude if longitude is not None else None,
                        "star_route_name": (
                            star_elem.get("routeName")
                            if star_elem is not None
                            else None
                        ),
                        "star_route_type": (
                            star_elem.get("routeType")
                            if star_elem is not None
                            else None
                        ),
                        "star_transition_fix": (
                            star_transition_elem.text.strip()
                            if star_transition_elem is not None
                            and star_transition_elem.text
                            else None
                        ),
                        "route_arrival_fix_name": (
                            route_arrival_elem.get("fixName")
                            if route_arrival_elem is not None
                            else None
                        ),
                        "route_arrival_fix_time": (
                            route_arrival_elem.get("arrTime")
                            if route_arrival_elem is not None
                            else None
                        ),
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
                            dict(rvsm_data_elem.attrib)
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
                        "sector_details": sector_details,
                        "airways": airways,
                        "centers": centers,
                        "route_of_flight": (
                            route_of_flight_elem.text
                            if route_of_flight_elem is not None
                            else None
                        ),
                        "track_data": track_data,
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
        logger.error(f"Error parsing trackInformation: {e}", exc_info=True)
        try:
            excerpt = etree.tostring(root, encoding="unicode")[:500]
        except Exception:
            excerpt = "(could not serialize root)"
        logger.error(f"Problematic XML (excerpt): {excerpt}")
        return []
