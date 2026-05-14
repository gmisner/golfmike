"""TFM FlightControl (ncsmFlightControl)."""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_flight_control(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "FlightControl":
            continue
        fc = message.find("fdm:ncsmFlightControl", namespaces=NAMESPACES)
        if fc is None:
            continue
        q = fc.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        etd = fc.find("nxcm:etd", namespaces=NAMESPACES)
        eta = fc.find("nxcm:eta", namespaces=NAMESPACES)
        ci = fc.find("nxcm:controlIndicator", namespaces=NAMESPACES)
        ctrl = fc.find("nxcm:ncsmControlData", namespaces=NAMESPACES)
        ctd = ctrl.find("nxcm:ctd", namespaces=NAMESPACES) if ctrl is not None else None
        cta = ctrl.find("nxcm:cta", namespaces=NAMESPACES) if ctrl is not None else None
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
                "etd_type": etd.get("etdType") if etd is not None else None,
                "etd_time": etd.get("timeValue") if etd is not None else None,
                "eta_type": eta.get("etaType") if eta is not None else None,
                "eta_time": eta.get("timeValue") if eta is not None else None,
                "control_indicator": (
                    ci.text.strip() if ci is not None and ci.text else None
                ),
                "ctd": ctd.text.strip() if ctd is not None and ctd.text else None,
                "cta": cta.text.strip() if cta is not None and cta.text else None,
                "raw_payload": etree.tostring(fc, encoding="unicode")[:8000],
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )
    logger.debug("parse_flight_control: {} row(s)", len(out))
    return out
