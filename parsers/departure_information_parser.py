"""
Parse TFM fltdMessage msgType=departureInformation → list of row dicts for storage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_departure_information(root: etree._Element) -> List[Dict[str, Any]]:
    messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
    out: List[Dict[str, Any]] = []
    for message in messages:
        if message.get("msgType") != "departureInformation":
            continue
        di = message.find("fdm:departureInformation", namespaces=NAMESPACES)
        if di is None:
            logger.debug("departureInformation: body missing")
            continue

        q = di.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        igtd_el = q.find("nxce:igtd", namespaces=NAMESPACES)
        dep = q.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
        arr = q.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)

        tod = di.find("nxcm:timeOfDeparture", namespaces=NAMESPACES)
        tod_text = tod.text.strip() if tod is not None and tod.text else None
        tod_est = tod.get("estimated") if tod is not None else None

        etd_time = None
        eta_time = None
        etd_type = None
        eta_type = None
        ftd = di.find("nxcm:ncsmFlightTimeData", namespaces=NAMESPACES)
        if ftd is not None:
            etd_el = ftd.find("nxcm:etd", namespaces=NAMESPACES)
            eta_el = ftd.find("nxcm:eta", namespaces=NAMESPACES)
            if etd_el is not None:
                etd_type = etd_el.get("etdType")
                etd_time = etd_el.get("timeValue")
            if eta_el is not None:
                eta_type = eta_el.get("etaType")
                eta_time = eta_el.get("timeValue")

        out.append(
            {
                "aircraft_id": (
                    aid.text.strip() if aid is not None and aid.text else None
                ),
                "gufi": (
                    gufi_el.text.strip()
                    if gufi_el is not None and gufi_el.text
                    else None
                ),
                "igtd": igtd_el.text if igtd_el is not None and igtd_el.text else None,
                "departure_airport": (
                    dep.text.strip() if dep is not None and dep.text else None
                ),
                "arrival_airport": (
                    arr.text.strip() if arr is not None and arr.text else None
                ),
                "time_of_departure": tod_text,
                "time_of_departure_estimated": tod_est,
                "etd_type": etd_type,
                "etd_time": etd_time,
                "eta_type": eta_type,
                "eta_time": eta_time,
                "source_facility": message.get("sourceFacility"),
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )

    logger.debug("parse_departure_information: {} row(s)", len(out))
    return out
