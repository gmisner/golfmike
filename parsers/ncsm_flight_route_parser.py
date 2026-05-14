"""
Parse TFM fltdMessage msgType=FlightRoute (ncsmFlightRoute), same body shape as schedule activate.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from parsers.ncsm_route_info_body import (
    extract_route_assignment_from_ncsm_route_info_body,
)
from utils.logger import main_logger as logger


def parse_flight_route(root: etree._Element) -> List[Dict[str, Any]]:
    messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
    out: List[Dict[str, Any]] = []
    for message in messages:
        if message.get("msgType") != "FlightRoute":
            continue
        body = message.find("fdm:ncsmFlightRoute", namespaces=NAMESPACES)
        if body is None:
            logger.debug("FlightRoute: ncsmFlightRoute missing")
            continue
        data = extract_route_assignment_from_ncsm_route_info_body(body, message)
        if data:
            out.append(data)
    logger.debug("parse_flight_route: {} row(s)", len(out))
    return out
