"""
Shared extractors for ncsmFlightRouteInformationType bodies (ScheduleActivate + FlightRoute).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger
from utils.nas_altitude import simple_altitude_hundreds_to_feet


def extract_route_assignment_from_ncsm_route_info_body(
    body: etree._Element, message: etree._Element
) -> Optional[Dict[str, Any]]:
    """
    body: ncsmFlightScheduleActivate or ncsmFlightRoute (same complex type in XSD).
    message: parent fdm:fltdMessage (attributes, flightRef, etc.).
    """
    if body is None:
        return None

    qualified_aircraft_id = body.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
    if qualified_aircraft_id is None:
        return None

    aircraft_id_elem = qualified_aircraft_id.find(
        "nxce:aircraftId", namespaces=NAMESPACES
    )
    aircraft_id = aircraft_id_elem.text if aircraft_id_elem is not None else None

    flight_ref = message.get("flightRef") or None
    gufi = message.get("gufi") or None
    if not gufi:
        gufi_el = qualified_aircraft_id.find("nxce:gufi", namespaces=NAMESPACES)
        gufi = gufi_el.text if gufi_el is not None else None
    if not gufi:
        logger.debug("ncsm route info: no gufi for aircraft {}", aircraft_id)

    igtd_el = qualified_aircraft_id.find("nxce:igtd", namespaces=NAMESPACES)
    igtd = igtd_el.text if igtd_el is not None else None

    dep_point = qualified_aircraft_id.find(
        "nxce:departurePoint/nxce:airport", namespaces=NAMESPACES
    )
    departure_airport = dep_point.text if dep_point is not None else None

    arr_point = qualified_aircraft_id.find(
        "nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES
    )
    arrival_airport = arr_point.text if arr_point is not None else None

    flight_status_elem = body.find(
        "nxcm:flightStatusAndSpec/nxcm:flightStatus", namespaces=NAMESPACES
    )
    flight_status = (
        flight_status_elem.text if flight_status_elem is not None else "PLANNED"
    )

    aircraft_model_elem = body.find(
        "nxcm:flightStatusAndSpec/nxcm:aircraftModel", namespaces=NAMESPACES
    )
    aircraft_model = (
        aircraft_model_elem.text if aircraft_model_elem is not None else None
    )

    altitude_elem = body.find(
        "nxcm:altitude/nxce:assignedAltitude/nxce:simpleAltitude", namespaces=NAMESPACES
    )
    assigned_altitude = None
    if altitude_elem is not None and altitude_elem.text:
        try:
            raw_fl = int(altitude_elem.text.replace("C", ""))
            assigned_altitude = simple_altitude_hundreds_to_feet(raw_fl)
        except ValueError:
            logger.warning("Invalid altitude value: {}", altitude_elem.text)

    speed_elem = body.find("nxcm:speed/nxce:filedTrueAirSpeed", namespaces=NAMESPACES)
    assigned_speed = None
    if speed_elem is not None and speed_elem.text:
        try:
            assigned_speed = int(speed_elem.text)
        except ValueError:
            logger.warning("Invalid speed value: {}", speed_elem.text)

    route_data_elem = body.find("nxcm:ncsmRouteData", namespaces=NAMESPACES)

    etd_elem = (
        route_data_elem.find("nxcm:etd", namespaces=NAMESPACES)
        if route_data_elem is not None
        else None
    )
    etd = etd_elem.get("timeValue") if etd_elem is not None else None

    eta_elem = (
        route_data_elem.find("nxcm:eta", namespaces=NAMESPACES)
        if route_data_elem is not None
        else None
    )
    eta = eta_elem.get("timeValue") if eta_elem is not None else None

    fixes = []
    if route_data_elem is not None:
        for fix_elem in route_data_elem.findall(
            "nxcm:flightTraversalData2/nxce:fix", namespaces=NAMESPACES
        ):
            fixes.append(
                {
                    "name": fix_elem.text,
                    "sequence_number": fix_elem.get("sequenceNumber"),
                    "elapsed_time": fix_elem.get("elapsedTime"),
                }
            )

    waypoints = []
    if route_data_elem is not None:
        for wp_elem in route_data_elem.findall(
            "nxcm:flightTraversalData2/nxce:waypoint", namespaces=NAMESPACES
        ):
            waypoints.append(
                {
                    "latitude": wp_elem.get("latitudeDecimal"),
                    "longitude": wp_elem.get("longitudeDecimal"),
                    "sequence_number": wp_elem.get("sequenceNumber"),
                    "elapsed_time": wp_elem.get("elapsedTime"),
                }
            )

    route_of_flight_elem = (
        route_data_elem.find("nxcm:routeOfFlight", namespaces=NAMESPACES)
        if route_data_elem is not None
        else None
    )
    route_of_flight = (
        route_of_flight_elem.text if route_of_flight_elem is not None else None
    )

    source_facility = message.get("sourceFacility") or None
    source_timestamp = message.get("sourceTimeStamp") or None

    route_data_dict = {
        "fixes": fixes,
        "waypoints": waypoints,
        "route_of_flight": route_of_flight,
        "etd": etd,
        "eta": eta,
        "diversion_indicator": None,
        "rvsm_data": None,
    }

    return {
        "aircraft_id": aircraft_id,
        "gufi": gufi,
        "flight_reference": flight_ref,
        "departure_airport": departure_airport,
        "arrival_airport": arrival_airport,
        "igtd": igtd,
        "flight_status": flight_status,
        "aircraft_model": aircraft_model,
        "assigned_altitude": assigned_altitude,
        "assigned_speed": assigned_speed,
        "route_data": route_data_dict,
        "etd": etd,
        "eta": eta,
        "source_facility": source_facility,
        "source_timestamp": source_timestamp,
    }
