"""
Parser for flightModification messages from the FAA SWIM FDPS feed.

These messages carry a *delta* — only the fields that changed — so we cannot
map them into FlightPlanModel (which needs the full record).  Instead we
return a normalised dict of whatever the message contains, keyed by GUFI, and
the storer does a targeted UPDATE against the existing flight-plan row.

Supported msgType values (register both in the registry):
    "flightModification"   — route / altitude / equipment amendments from ERAM
    "FlightModify"         — alternate casing seen on some SWIM streams
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from dateutil.parser import isoparse
from lxml import etree

from parsers.flight_sectors_parser import NAMESPACES
from utils.logger import main_logger as logger


def _text(el: Optional[etree._Element]) -> Optional[str]:
    """Safe .text access — returns None when element is absent."""
    return el.text.strip() if el is not None and el.text else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string to a UTC-aware datetime, or return None."""
    if not value:
        return None
    try:
        dt = isoparse(value.strip())
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def parse_flight_modify(root: etree._Element) -> Optional[dict[str, Any]]:
    """
    Parse a SWIM flightModification message.

    Returns a dict with keys:
        gufi, aircraft_id, departure_airport, arrival_airport,
        departure_time, route_text, aircraft_type,
        source_facility, source_time, amendment_type
    or None on hard parse failure.
    """
    try:
        result: dict[str, Any] = {"amendment_type": "MODIFY"}

        # ── Try airlineData wrapper (FDPS airline format) ──────────────────────
        airline_data = root.find(".//nxcm:airlineData", namespaces=NAMESPACES)

        if airline_data is not None:
            # Aircraft ID + GUFI from flightStatusAndSpec
            fss = airline_data.find(".//nxcm:flightStatusAndSpec", namespaces=NAMESPACES)
            if fss is not None:
                result["aircraft_id"] = _text(fss.find("nxce:aircraftId", namespaces=NAMESPACES))
                result["gufi"] = _text(fss.find("nxce:gufi", namespaces=NAMESPACES))
                spec = fss.find("nxcm:aircraftSpecification", namespaces=NAMESPACES)
                if spec is not None:
                    result["aircraft_type"] = spec.get("aircraftType")

            # Timing attributes on flightTimeData
            ftd = airline_data.find(".//nxcm:flightTimeData", namespaces=NAMESPACES)
            if ftd is not None:
                result["departure_time"] = _parse_dt(ftd.get("igtd"))
                result["arrival_time"] = _parse_dt(ftd.get("eta"))

            # Route
            rof = airline_data.find(".//nxcm:routeOfFlight", namespaces=NAMESPACES)
            result["route_text"] = _text(rof)

            # Arrival fix (attribute keys use raw XML names without @)
            arr_fix = airline_data.find(".//nxcm:arrivalFixAndTime", namespaces=NAMESPACES)
            if arr_fix is not None:
                result["arrival_fix"] = arr_fix.get("fixName")
                result["arrival_fix_time"] = _parse_dt(arr_fix.get("arrTime"))

        # ── Fallback: qualifiedAircraftId pattern (shared with trackInformation) ──
        qaid = root.find(".//nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if qaid is None:
            qaid = root.find(".//nxce:qualifiedAircraftId", namespaces=NAMESPACES)
        if qaid is not None:
            result.setdefault("aircraft_id", _text(qaid.find("nxce:aircraftId", namespaces=NAMESPACES)))
            result.setdefault("gufi", _text(qaid.find("nxce:gufi", namespaces=NAMESPACES)))
            result.setdefault("departure_time", _parse_dt(
                _text(qaid.find("nxce:igtd", namespaces=NAMESPACES))
            ))
            dep = qaid.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
            arr = qaid.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)
            result.setdefault("departure_airport", _text(dep))
            result.setdefault("arrival_airport", _text(arr))

        # ── ncsmRouteData fallback ─────────────────────────────────────────────
        if not result.get("route_text"):
            rof2 = root.find(".//nxcm:routeOfFlight", namespaces=NAMESPACES)
            result["route_text"] = _text(rof2)

        # ── Source metadata from the fltdMessage element ───────────────────────
        for msg in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
            result.setdefault("source_facility", msg.get("sourceFacility") or msg.get("facility"))
            result.setdefault("source_time", _parse_dt(msg.get("sourceTimeStamp") or msg.get("timestamp")))
            break

        if not result.get("gufi"):
            logger.warning("flightModification message has no GUFI — cannot update record")
            return None

        logger.debug(
            f"Parsed flightModification for {result.get('aircraft_id')} / {result.get('gufi')}: "
            f"route={'yes' if result.get('route_text') else 'no'}"
        )
        return result

    except Exception as e:
        logger.error(f"Error parsing flightModification: {e}", exc_info=True)
        return None
