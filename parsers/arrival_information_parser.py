"""Parse TFM fltdMessage msgType=arrivalInformation."""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_arrival_information(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "arrivalInformation":
            continue
        ai = message.find("fdm:arrivalInformation", namespaces=NAMESPACES)
        if ai is None:
            continue
        q = ai.find("nxce:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            q = ai.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        dep = q.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
        arr = q.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)

        toa = ai.find("nxce:timeOfArrival", namespaces=NAMESPACES)
        if toa is None:
            toa = ai.find("nxcm:timeOfArrival", namespaces=NAMESPACES)
        toa_text = toa.text.strip() if toa is not None and toa.text else None
        ftd = ai.find("nxcm:ncsmFlightTimeData", namespaces=NAMESPACES)
        etd_t = etd_ty = eta_t = eta_ty = None
        if ftd is not None:
            etd_el = ftd.find("nxcm:etd", namespaces=NAMESPACES)
            eta_el = ftd.find("nxcm:eta", namespaces=NAMESPACES)
            if etd_el is not None:
                etd_ty = etd_el.get("etdType")
                etd_t = etd_el.get("timeValue")
            if eta_el is not None:
                eta_ty = eta_el.get("etaType")
                eta_t = eta_el.get("timeValue")
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
                "departure_airport": (
                    dep.text.strip() if dep is not None and dep.text else None
                ),
                "arrival_airport": (
                    arr.text.strip() if arr is not None and arr.text else None
                ),
                "time_of_arrival": toa_text,
                "etd_type": etd_ty,
                "etd_time": etd_t,
                "eta_type": eta_ty,
                "eta_time": eta_t,
                "source_facility": message.get("sourceFacility"),
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )
    logger.debug("parse_arrival_information: {} row(s)", len(out))
    return out
