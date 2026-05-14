"""TFM beaconCodeInformation."""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_beacon_code_information(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "beaconCodeInformation":
            continue
        bc = message.find("fdm:beaconCodeInformation", namespaces=NAMESPACES)
        if bc is None:
            continue
        q = bc.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        beacon = bc.find("nxce:beaconCode", namespaces=NAMESPACES)
        code = None
        if beacon is not None:
            if beacon.text:
                code = beacon.text.strip()
            for k, v in beacon.attrib.items():
                if v and not code:
                    code = v
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
                "beacon_code": code,
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )
    logger.debug("parse_beacon_code_information: {} row(s)", len(out))
    return out
