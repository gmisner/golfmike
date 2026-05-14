"""TFM oceanicReport."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lxml import etree

from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.aircraft_id import normalize_aircraft_id
from utils.logger import main_logger as logger


def _dms_to_decimal(coord_el: etree._Element, kind: str) -> Optional[str]:
    """
    Convert nxce:latitude / nxce:longitude DMS structure to decimal string.
    kind must be "latitude" or "longitude".
    """
    node_name = f"{kind}DMS"
    dms = coord_el.find(f"nxce:{node_name}", namespaces=NAMESPACES)
    if dms is None:
        return None
    try:
        deg = float((dms.get("degrees") or "").strip())
        mins = float((dms.get("minutes") or "0").strip())
        secs = float((dms.get("seconds") or "0").strip())
        dec = deg + mins / 60.0 + secs / 3600.0
        direction = (dms.get("direction") or "").strip().upper()
        if direction in ("S", "SOUTH", "W", "WEST"):
            dec = -dec
        return f"{dec:.8f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return None


def _text_or_none(el: Optional[etree._Element]) -> Optional[str]:
    if el is None or el.text is None:
        return None
    s = el.text.strip()
    return s or None


def parse_oceanic_report(root: etree._Element) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
        if message.get("msgType") != "oceanicReport":
            continue
        orp = message.find("fdm:oceanicReport", namespaces=NAMESPACES)
        if orp is None:
            continue
        q = orp.find("nxcm:qualifiedAircraftId", namespaces=NAMESPACES)
        if q is None:
            continue
        aid = _text_or_none(q.find("nxce:aircraftId", namespaces=NAMESPACES))
        gufi_el = q.find("nxce:gufi", namespaces=NAMESPACES)
        igtd = _text_or_none(q.find("nxce:igtd", namespaces=NAMESPACES))
        dep_airport = _text_or_none(
            q.find("nxce:departurePoint/nxce:airport", namespaces=NAMESPACES)
        )
        arr_airport = _text_or_none(
            q.find("nxce:arrivalPoint/nxce:airport", namespaces=NAMESPACES)
        )
        aircraft_category = q.get("aircraftCategory")
        user_category = q.get("userCategory")
        speed_el = orp.find("nxcm:speed", namespaces=NAMESPACES)
        if speed_el is None:
            for ch in orp:
                if etree.QName(ch).localname == "speed":
                    speed_el = ch
                    break
        speed = (
            speed_el.text.strip() if speed_el is not None and speed_el.text else None
        )
        rep = orp.find("nxcm:reportedPositionData", namespaces=NAMESPACES)
        if rep is None:
            for ch in orp:
                if etree.QName(ch).localname == "reportedPositionData":
                    rep = ch
                    break
        reported = (
            etree.tostring(rep, encoding="unicode")[:4000] if rep is not None else None
        )
        latitude = None
        longitude = None
        altitude = None
        position_time = None
        if rep is not None:
            latitude = _dms_to_decimal(
                rep.find("nxcm:position/nxce:latitude", namespaces=NAMESPACES),
                "latitude",
            )
            longitude = _dms_to_decimal(
                rep.find("nxcm:position/nxce:longitude", namespaces=NAMESPACES),
                "longitude",
            )
            altitude = _text_or_none(rep.find("nxce:altitude", namespaces=NAMESPACES))
            position_time = _text_or_none(rep.find("nxce:time", namespaces=NAMESPACES))

        eta_el = orp.find(
            "nxcm:ncsmTrackData/nxcm:eta[@etaType='ESTIMATED']",
            namespaces=NAMESPACES,
        ) or orp.find("nxcm:ncsmTrackData/nxcm:eta", namespaces=NAMESPACES)
        eta_time = eta_el.get("timeValue") if eta_el is not None else None
        rvsm_el = orp.find("nxcm:ncsmTrackData/nxcm:rvsmData", namespaces=NAMESPACES)
        rvsm_data = (
            {
                "equipped": rvsm_el.get("equipped"),
                "current_compliance": rvsm_el.get("currentCompliance"),
                "future_compliance": rvsm_el.get("futureCompliance"),
            }
            if rvsm_el is not None
            else None
        )

        out.append(
            {
                "aircraft_id": normalize_aircraft_id(aid),
                "gufi": (
                    gufi_el.text.strip()
                    if gufi_el is not None and gufi_el.text
                    else None
                ),
                "igtd": igtd,
                "departure_airport": dep_airport,
                "arrival_airport": arr_airport,
                "aircraft_category": aircraft_category,
                "user_category": user_category,
                "speed": speed,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "position_time": position_time,
                "eta_estimated": eta_time,
                "rvsm_data": rvsm_data,
                "reported_position_snippet": reported,
                "raw_payload": etree.tostring(orp, encoding="unicode")[:8000],
                "source_timestamp": message.get("sourceTimeStamp"),
                "flight_reference": message.get("flightRef"),
                "source_facility": message.get("sourceFacility"),
                "fd_trigger": message.get("fdTrigger"),
            }
        )
    logger.debug("parse_oceanic_report: {} row(s)", len(out))
    return out
