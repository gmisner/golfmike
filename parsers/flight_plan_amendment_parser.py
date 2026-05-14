"""
Parser for flightAmendment messages from the FAA SWIM FDPS feed.

Amendment messages use a qualifiedAircraftId + amendmentData structure and
carry only the fields that changed.  We return a normalised dict (same shape
as flight_modify_parser) so both can share the same storer.

Supported msgType values:
    "flightAmendment"   — filed amendment (route, altitude, equipment change)
    "FlightAmendment"   — alternate casing
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from dateutil.parser import isoparse
from lxml import etree

from parsers.flight_sectors_parser import NAMESPACES
from utils.logger import main_logger as logger


def _text(el: Optional[etree._Element]) -> Optional[str]:
    return el.text.strip() if el is not None and el.text else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = isoparse(value.strip())
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def parse_flight_plan_amendment(root: etree._Element) -> Optional[dict[str, Any]]:
    """
    Parse a SWIM flightAmendment message.

    Returns the same normalised dict shape as parse_flight_modify:
        gufi, aircraft_id, departure_airport, arrival_airport,
        departure_time, route_text, aircraft_type,
        source_facility, source_time, amendment_type
    or None on hard parse failure.
    """
    try:
        result: dict[str, Any] = {"amendment_type": "AMEND"}

        # ── qualifiedAircraftId — flight identity ─────────────────────────────
        qaid = root.find(".//nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if qaid is None:
            qaid = root.find(".//nxce:qualifiedAircraftId", namespaces=NAMESPACES)

        if qaid is not None:
            result["aircraft_id"] = _text(qaid.find("nxce:aircraftId", namespaces=NAMESPACES))
            result["gufi"] = _text(qaid.find("nxce:gufi", namespaces=NAMESPACES))

            # Computer ID carries some ERAM internal identifier — grab for tracing
            comp_id = qaid.find("nxce:computerId", namespaces=NAMESPACES)
            if comp_id is not None:
                for child in comp_id:
                    tag = etree.QName(child).localname
                    result[f"computer_{tag}"] = child.text

            result["departure_time"] = _parse_dt(
                _text(qaid.find("nxce:igtd", namespaces=NAMESPACES))
            )
            dep = qaid.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
            arr = qaid.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)
            result["departure_airport"] = _text(dep)
            result["arrival_airport"] = _text(arr)

        # ── amendmentData — the actual delta ──────────────────────────────────
        amd = root.find(".//nxcm:amendmentData", namespaces=NAMESPACES)
        if amd is not None:
            for child in amd:
                tag = etree.QName(child).localname

                if tag == "newFlightAircraftSpecs":
                    result["aircraft_type"] = child.get("aircraftType") or child.text

                elif tag == "newFlightRoute":
                    result["route_text"] = _text(child)

                elif tag == "newSpeed":
                    for speed_child in child:
                        result["new_speed"] = speed_child.text
                        break

                elif tag == "newCoordinationTime":
                    for k, v in child.attrib.items():
                        result[f"coord_{k}"] = _parse_dt(v) if "time" in k.lower() else v
                    result["new_coord_time"] = child.text

                elif tag in ("newDeparturePoint", "newArrivalPoint"):
                    apt = child.find("nxce:airport", namespaces=NAMESPACES)
                    key = "departure_airport" if "Departure" in tag else "arrival_airport"
                    result[key] = _text(apt)

                elif tag == "newIgtd":
                    result["departure_time"] = _parse_dt(_text(child))

                else:
                    result[f"amd_{tag}"] = _text(child)

        # ── Source metadata ────────────────────────────────────────────────────
        for msg in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
            result.setdefault("source_facility", msg.get("sourceFacility") or msg.get("facility"))
            result.setdefault("source_time", _parse_dt(msg.get("sourceTimeStamp") or msg.get("timestamp")))
            break

        if not result.get("gufi"):
            logger.warning("flightAmendment message has no GUFI — cannot update record")
            return None

        logger.debug(
            f"Parsed flightAmendment for {result.get('aircraft_id')} / {result.get('gufi')}: "
            f"route={'yes' if result.get('route_text') else 'no'}, "
            f"ac_type={result.get('aircraft_type')}"
        )
        return result

    except Exception as e:
        logger.error(f"Error parsing flightAmendment: {e}", exc_info=True)
        return None
