"""TFM fltdMessage msgType=flightPlanCancellation."""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_flight_plan_cancellation(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "flightPlanCancellation":
            continue
        can = message.find("fdm:flightPlanCancellation", namespaces=NAMESPACES)
        if can is None:
            continue
        q = can.find("nxce:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            q = can.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
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
                "source_facility": message.get("sourceFacility"),
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )
    logger.debug("parse_flight_plan_cancellation: {} row(s)", len(out))
    return out
