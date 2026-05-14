"""
Parse FAA NAS FIXM MessageCollection (e.g. FDPS queue) into TrackInformationModel rows.

Root: {http://www.faa.aero/nas/3.0}MessageCollection — no TFM msgType attribute.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from lxml import etree

from models.pydantic.track_information import TrackInformationModel
from parsers.xml_namespaces import SWIM_XML_PARSER
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger


def _local(el: etree._Element) -> str:
    return etree.QName(el).localname


def _child_by_local(parent: etree._Element, name: str) -> Optional[etree._Element]:
    for c in parent:
        if _local(c) == name:
            return c
    return None


def _first_descendant_local(
    parent: etree._Element, name: str
) -> Optional[etree._Element]:
    for el in parent.iter():
        if el is not parent and _local(el) == name:
            return el
    return None


def _first_descendant_text(parent: etree._Element, name: str) -> Optional[str]:
    el = _first_descendant_local(parent, name)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _coordination_fields(
    flight: etree._Element,
) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
    coordination = _child_by_local(flight, "coordination")
    if coordination is None:
        return None, None, None, None

    coordination_time = coordination.get("coordinationTime")
    fix_el = _child_by_local(coordination, "coordinationFix")
    if fix_el is None:
        return coordination_time, None, None, None

    fix_name = fix_el.get("fix")
    distance_nm = _float_text(_child_by_local(fix_el, "distance"))
    radial_deg = _float_text(_child_by_local(fix_el, "radial"))
    return coordination_time, fix_name, distance_nm, radial_deg


def _parse_pos_text(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not text or not text.strip():
        return None, None
    parts = text.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def _float_text(elem: Optional[etree._Element]) -> Optional[float]:
    if elem is None or elem.text is None:
        return None
    try:
        return float(elem.text.strip())
    except ValueError:
        return None


def _parse_aircraft_position(
    ap: etree._Element,
) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int], Optional[str]]:
    """From NasAircraftPositionType element: lat, lon, alt_ft, speed_kts, time."""
    lat, lon = None, None
    for el in ap.iter():
        if _local(el) == "pos" and el.text:
            lat, lon = _parse_pos_text(el.text)
            if lat and lon:
                break

    alt_el = _child_by_local(ap, "altitude")
    alt = None
    if alt_el is not None and alt_el.text:
        try:
            alt = int(round(float(alt_el.text.strip())))
        except ValueError:
            pass

    speed = None
    for el in ap.iter():
        if _local(el) == "actualSpeed":
            sur = _child_by_local(el, "surveillance")
            if sur is not None and sur.text:
                try:
                    speed = int(round(float(sur.text.strip())))
                except ValueError:
                    pass
            break

    time_at = ap.get("positionTime") or ap.get("targetPositionTime")

    return lat, lon, alt, speed, time_at


def _parse_flight_message(flight: etree._Element) -> Optional[TrackInformationModel]:
    ident = _child_by_local(flight, "flightIdentification")
    aircraft_id = normalize_aircraft_id(
        ident.get("aircraftIdentification") if ident is not None else None
    )

    gufi_el = _child_by_local(flight, "gufi")
    gufi = gufi_el.text.strip() if gufi_el is not None and gufi_el.text else ""

    dep = _child_by_local(flight, "departure")
    arr = _child_by_local(flight, "arrival")
    departure_airport = dep.get("departurePoint", "") if dep is not None else ""
    arrival_airport = arr.get("arrivalPoint", "") if arr is not None else ""

    airline = ""
    op = _child_by_local(flight, "operator")
    if op is not None:
        org = _first_descendant_local(op, "organization")
        if org is not None:
            airline = org.get("name") or ""

    enroute = _child_by_local(flight, "enRoute")
    aircraft_pos = None
    if enroute is not None:
        for ch in enroute:
            if _local(ch) == "position":
                aircraft_pos = ch
                break

    lat: Optional[str] = None
    lon: Optional[str] = None
    alt: Optional[int] = None
    speed: Optional[int] = None
    time_at: Optional[str] = None
    if aircraft_pos is not None:
        lat, lon, alt, speed, time_at = _parse_aircraft_position(aircraft_pos)

    if speed is None:
        requested_speed = _first_descendant_text(flight, "nasAirspeed")
        if requested_speed:
            try:
                speed = int(round(float(requested_speed)))
            except ValueError:
                speed = None

    if alt is None:
        alt = 0

    flight_status = ""
    flight_status_el = _child_by_local(flight, "flightStatus")
    if flight_status_el is not None:
        flight_status = flight_status_el.get("fdpsFlightStatus") or ""

    current_beacon_code = _first_descendant_text(flight, "currentBeaconCode")
    route_text = ""
    agreed = _child_by_local(flight, "agreed")
    if agreed is not None:
        route = _child_by_local(agreed, "route")
        if route is not None:
            route_text = route.get("nasRouteText") or ""

    source_timestamp = flight.get("timestamp")
    has_position = lat is not None and lon is not None
    (
        coordination_time,
        coordination_fix,
        coordination_distance_nm,
        coordination_radial_deg,
    ) = _coordination_fields(flight)

    return TrackInformationModel(
        aircraft_id=aircraft_id,
        gufi=gufi,
        speed=speed,
        altitude=alt,
        latitude=lat,
        longitude=lon,
        time_at_position=time_at,
        departure_airport=departure_airport or "",
        arrival_airport=arrival_airport or "",
        airline=airline,
        aircraft_category="",
        user_category="",
        etd=None,
        eta=None,
        diversion_indicator=None,
        rvsm_data=None,
        next_position=None,
        fixes=[],
        waypoints=[],
        sectors=[],
        route_of_flight=None,
        track_data={
            "nas_message_collection": {
                "has_position": has_position,
                "flight_status": flight_status or None,
                "current_beacon_code": current_beacon_code,
                "route_text": route_text or None,
                "source_timestamp": source_timestamp,
                "coordination_time": coordination_time,
                "coordination_fix": coordination_fix,
                "coordination_distance_nm": coordination_distance_nm,
                "coordination_radial_deg": coordination_radial_deg,
            }
        },
    )


def parse_nas_message_collection(root: etree._Element) -> List[TrackInformationModel]:
    """Parse NAS 3.0 MessageCollection; one track row per message/flight with position."""
    out: List[TrackInformationModel] = []
    if _local(root) != "MessageCollection":
        logger.warning(
            "parse_nas_message_collection: expected MessageCollection root, got %s",
            _local(root),
        )
        return out

    for msg in root:
        if _local(msg) != "message":
            continue
        flight = _child_by_local(msg, "flight")
        if flight is None:
            continue
        try:
            row = _parse_flight_message(flight)
            if row is not None:
                out.append(row)
        except Exception as e:
            logger.error("NAS message parse error: %s", e, exc_info=True)

    logger.debug("parse_nas_message_collection: %s flights", len(out))
    return out


def parse_nas_message_collection_xml(xml_string: str) -> List[TrackInformationModel]:
    """Convenience: parse XML string to list of TrackInformationModel."""
    root = etree.fromstring(xml_string.encode("utf-8"), parser=SWIM_XML_PARSER)
    return parse_nas_message_collection(root)
