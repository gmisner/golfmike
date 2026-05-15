"""
TBFM Parser — FAA SWIM TMA Metering Publication

Real schema (namespace urn:us:gov:dot:faa:atm:tfm:tbfmmeteringpublication:1.1.0):

  <env envTime="..." envSrce="TMA.ZNY.FAA.GOV">
    <tma msgTime="..." msgId="...">
      <air gufi="..." cid="..." tmaId="..." apt="EWR" dap="LAX" aid="UAL1700" airType="AMD">
        <flt>
          <aid>UAL1700</aid>
          <dap>LAX</dap>
          <apt>EWR</apt>
          <fps>DEPARTED</fps>    <!-- flight phase status -->
          <acs>ACTIVE</acs>      <!-- aircraft status -->
          <ctm>2026-05-15T03:09:00Z</ctm>  <!-- controlled time (metering time) -->
          <a10>route string</a10>
        </flt>
      </air>
    </tma>
  </env>

  <mis misTime="..." misSrce="..."><hb/></mis>  <!-- heartbeat, skip -->
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from lxml import etree
from utils.logger import main_logger as logger

NS = "urn:us:gov:dot:faa:atm:tfm:tbfmmeteringpublication:1.1.0"


def _text(el: etree._Element, tag: str) -> str | None:
    child = el.find(f"{{{NS}}}{tag}")
    if child is None:
        child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


class TBFMParser:
    def parse(self, payload: bytes | str) -> list[dict]:
        if isinstance(payload, str):
            payload = payload.encode("utf-8", errors="replace")
        try:
            root = etree.fromstring(payload)
        except etree.XMLSyntaxError as exc:
            logger.warning("TBFM: XML parse error: %s", exc)
            return [{"record_type": "raw", "raw_xml": payload, "root_element": None,
                     "parse_error": str(exc)}]

        local = etree.QName(root).localname

        if local == "mis":
            return []  # heartbeat — nothing to store

        if local == "env":
            return self._parse_env(root)

        logger.debug("TBFM: unrecognised root <%s>", local)
        return [{"record_type": "raw", "raw_xml": payload, "root_element": local}]

    def _parse_env(self, env: etree._Element) -> list[dict]:
        records: list[dict] = []
        env_time = env.get("envTime")
        env_src  = env.get("envSrce", "")

        for tma in env:
            if etree.QName(tma).localname != "tma":
                continue
            msg_time = _parse_dt(tma.get("msgTime") or env_time)

            for air in tma:
                if etree.QName(air).localname != "air":
                    continue
                rec = self._parse_air(air, msg_time, env_src)
                if rec:
                    records.append(rec)

        return records

    def _parse_air(self, air: etree._Element, msg_time: datetime | None,
                   env_src: str) -> dict | None:
        gufi       = air.get("gufi")
        aircraft_id = air.get("aid")
        airport    = air.get("apt")       # arrival airport
        dep_airport = air.get("dap")      # departure airport
        air_type   = air.get("airType")   # AMD, NEW, DEL, etc.
        tma_id     = air.get("tmaId")
        cid        = air.get("cid")

        # Pull fields from <flt> child
        flt = None
        for child in air:
            if etree.QName(child).localname == "flt":
                flt = child
                break

        ctm_str = _text(flt, "ctm") if flt is not None else None
        etm_str = _text(flt, "etm") if flt is not None else None
        fps     = _text(flt, "fps") if flt is not None else None  # flight phase
        acs     = _text(flt, "acs") if flt is not None else None  # aircraft status

        scheduled_time = _parse_dt(ctm_str) or _parse_dt(etm_str)

        extra: dict = {}
        if dep_airport:
            extra["dep_airport"] = dep_airport
        if tma_id:
            extra["tma_id"] = tma_id
        if cid:
            extra["cid"] = cid
        if env_src:
            extra["env_src"] = env_src
        if fps:
            extra["fps"] = fps
        if acs:
            extra["acs"] = acs

        return {
            "record_type":      "metering_flight",
            "received_at":      msg_time or datetime.now(timezone.utc),
            "publication_type": air_type,
            "airport":          airport,
            "aircraft_id":      aircraft_id,
            "gufi":             gufi,
            "meter_fix":        None,   # not in this schema; tmaId is the sequence ID
            "scheduled_time":   scheduled_time,
            "actual_time":      None,
            "sequence_number":  None,
            "delay_minutes":    None,
            "arrival_runway":   None,
            "flight_status":    acs,
            "extra_data":       extra if extra else None,
        }
