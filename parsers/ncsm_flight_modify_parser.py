"""
Parse TFM fltdMessage msgType=FlightModify (ncsmFlightModify) → flight_plan_traffic-shaped dicts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_ncsm_flight_modify(root: etree._Element) -> List[Dict[str, Any]]:
    messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
    parsed: List[Dict[str, Any]] = []

    for message in messages:
        if message.get("msgType") != "FlightModify":
            continue
        mod = message.find("fdm:ncsmFlightModify", namespaces=NAMESPACES)
        if mod is None:
            logger.debug("FlightModify: ncsmFlightModify missing")
            continue

        q = mod.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue

        aircraft_id = None
        gufi = None
        igtd = None
        dep = None
        arr = None

        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        if aid is not None and aid.text:
            aircraft_id = aid.text.strip()

        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        if gufi_el is not None and gufi_el.text:
            gufi = gufi_el.text.strip()

        igtd_el = q.find("nxce:igtd", namespaces=NAMESPACES)
        if igtd_el is not None and igtd_el.text:
            igtd = igtd_el.text

        dep_el = q.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
        if dep_el is not None and dep_el.text:
            dep = dep_el.text.strip()

        arr_el = q.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)
        if arr_el is not None and arr_el.text:
            arr = arr_el.text.strip()

        status_text = None
        aircraft_type = None
        route_text = None

        ad = mod.find("nxcm:airlineData", namespaces=NAMESPACES)
        if ad is not None:
            fss = ad.find("nxcm:flightStatusAndSpec", namespaces=NAMESPACES)
            if fss is not None:
                st = fss.find("nxcm:flightStatus", namespaces=NAMESPACES)
                if st is not None and st.text:
                    status_text = st.text.strip()
                am = fss.find("nxcm:aircraftModel", namespaces=NAMESPACES)
                if am is not None and am.text:
                    aircraft_type = am.text.strip()

            fr = ad.find("nxcm:arrivalFixAndTime", namespaces=NAMESPACES)
            if fr is not None:
                fn = fr.get("fixName")
                if fn:
                    route_text = f"arrFix={fn}"

        if not aircraft_id:
            logger.warning("FlightModify: no aircraft_id")
            continue

        parsed.append(
            {
                "aircraft_id": aircraft_id,
                "gufi": gufi,
                "flight_reference": message.get("flightRef"),
                "departure_airport": dep or message.get("depArpt"),
                "arrival_airport": arr or message.get("arrArpt"),
                "igtd": igtd,
                "aircraft_type": aircraft_type,
                "route_text": route_text,
                "source_facility": message.get("sourceFacility"),
                "source_timestamp": message.get("sourceTimeStamp"),
                "status": status_text or "PLANNED",
            }
        )

    logger.debug("parse_ncsm_flight_modify: {} row(s)", len(parsed))
    return parsed
