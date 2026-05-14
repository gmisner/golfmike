"""TFM boundaryCrossingUpdate."""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_boundary_crossing_update(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "boundaryCrossingUpdate":
            continue
        b = message.find("fdm:boundaryCrossingUpdate", namespaces=NAMESPACES)
        if b is None:
            continue
        q = b.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        bp = b.find("nxcm:boundaryPosition", namespaces=NAMESPACES)
        bc_time = bp.get("boundaryCrossingTime") if bp is not None else None
        fix_name = None
        if bp is not None:
            nfx = bp.find("nxce:namedFix", namespaces=NAMESPACES)
            if nfx is not None and nfx.text:
                fix_name = nfx.text.strip()
            elif bp.text:
                fix_name = bp.text.strip()
        route_el = b.find("nxcm:routeOfFlight", namespaces=NAMESPACES)
        route_text = (
            route_el.text.strip() if route_el is not None and route_el.text else None
        )
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
                "boundary_crossing_time": bc_time,
                "boundary_fix": fix_name,
                "route_of_flight": route_text,
                "raw_payload": (etree.tostring(b, encoding="unicode")[:8000]),
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )
    logger.debug("parse_boundary_crossing_update: {} row(s)", len(out))
    return out
