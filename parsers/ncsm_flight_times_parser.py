"""
Parse TFM fltdMessage msgType=FlightTimes (ncsmFlightTimes) → dicts for flights hub update.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_flight_times(root: etree._Element) -> List[Dict[str, Any]]:
    messages = root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES)
    out: List[Dict[str, Any]] = []

    for message in messages:
        if message.get("msgType") != "FlightTimes":
            continue
        ft = message.find("fdm:ncsmFlightTimes", namespaces=NAMESPACES)
        if ft is None:
            for ch in list(message):
                if etree.QName(ch).localname == "ncsmFlightTimes":
                    ft = ch
                    break
        if ft is None:
            logger.debug("FlightTimes: ncsmFlightTimes missing")
            continue

        q = ft.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue

        aid = q.find("nxce:aircraftId", namespaces=NAMESPACES)
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        igtd_el = q.find("nxce:igtd", namespaces=NAMESPACES)
        dep = q.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
        arr = q.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)

        etd_el = ft.find("nxcm:etd", namespaces=NAMESPACES)
        eta_el = ft.find("nxcm:eta", namespaces=NAMESPACES)
        ctd_el = ft.find("nxcm:ctd", namespaces=NAMESPACES)
        cta_el = ft.find("nxcm:cta", namespaces=NAMESPACES)

        fss = ft.find("nxcm:flightStatusAndSpec", namespaces=NAMESPACES)
        flight_status = None
        if fss is not None:
            st = fss.find("nxcm:flightStatus", namespaces=NAMESPACES)
            if st is not None and st.text:
                flight_status = st.text.strip()

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
                "etd_type": etd_el.get("etdType") if etd_el is not None else None,
                "etd_time": etd_el.get("timeValue") if etd_el is not None else None,
                "eta_type": eta_el.get("etaType") if eta_el is not None else None,
                "eta_time": eta_el.get("timeValue") if eta_el is not None else None,
                "ctd": (
                    ctd_el.text.strip() if ctd_el is not None and ctd_el.text else None
                ),
                "cta": (
                    cta_el.text.strip() if cta_el is not None and cta_el.text else None
                ),
                "flight_status": flight_status,
                "source_facility": message.get("sourceFacility"),
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
            }
        )

    logger.debug("parse_flight_times: {} row(s)", len(out))
    return out
