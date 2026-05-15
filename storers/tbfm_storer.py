"""
TBFM Storer — persists parsed TBFM metering records to PostgreSQL.

Tables:
  tbfm_metering_flights  – per-flight meter-fix schedule / sequence / delay
  tbfm_tmis              – Traffic Management Initiatives (GDP, AFP, GS, …)
  tbfm_raw_messages      – raw XML samples (for unknown / unparseable messages)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from utils.logger import main_logger as logger
from db_config import SessionLocal


class TBFMStorer:
    def store(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        session = SessionLocal()
        stored = 0
        try:
            for rec in records:
                rt = rec.get("record_type")
                if rt == "metering_flight":
                    self._upsert_metering_flight(session, rec)
                    stored += 1
                elif rt == "tmi":
                    self._upsert_tmi(session, rec)
                    stored += 1
                elif rt == "raw":
                    self._store_raw(session, rec)
                    stored += 1
                else:
                    logger.warning("TBFM storer: unknown record_type=%s", rt)
            session.commit()
        except Exception as exc:
            logger.error("TBFM storer error: %s", exc, exc_info=True)
            session.rollback()
        finally:
            session.close()
        return stored

    # ── metering_flights ──────────────────────────────────────────────────────

    def _upsert_metering_flight(self, session, rec: dict) -> None:
        """
        Upsert on (gufi, meter_fix) when both are available; otherwise insert.
        """
        extra = rec.get("extra_data")
        extra_json = json.dumps(extra) if extra else None

        # Try update first if we have a natural key
        if rec.get("gufi") and rec.get("meter_fix"):
            result = session.execute(
                text("""
                    UPDATE tbfm_metering_flights SET
                        aircraft_id      = :aircraft_id,
                        airport          = :airport,
                        publication_type = :publication_type,
                        scheduled_time   = :scheduled_time,
                        actual_time      = :actual_time,
                        sequence_number  = :sequence_number,
                        delay_minutes    = :delay_minutes,
                        arrival_runway   = :arrival_runway,
                        flight_status    = :flight_status,
                        extra_data       = CAST(:extra_data AS JSONB),
                        updated_at       = NOW()
                    WHERE gufi = :gufi AND meter_fix = :meter_fix
                    RETURNING id
                """),
                {
                    "gufi":             rec.get("gufi"),
                    "meter_fix":        rec.get("meter_fix"),
                    "aircraft_id":      rec.get("aircraft_id"),
                    "airport":          rec.get("airport"),
                    "publication_type": rec.get("publication_type"),
                    "scheduled_time":   rec.get("scheduled_time"),
                    "actual_time":      rec.get("actual_time"),
                    "sequence_number":  rec.get("sequence_number"),
                    "delay_minutes":    rec.get("delay_minutes"),
                    "arrival_runway":   rec.get("arrival_runway"),
                    "flight_status":    rec.get("flight_status"),
                    "extra_data":       extra_json,
                },
            )
            if result.fetchone():
                return  # updated existing row

        # Insert new row
        session.execute(
            text("""
                INSERT INTO tbfm_metering_flights
                    (received_at, publication_type, airport, aircraft_id, gufi,
                     meter_fix, scheduled_time, actual_time, sequence_number,
                     delay_minutes, arrival_runway, flight_status, extra_data)
                VALUES
                    (:received_at, :publication_type, :airport, :aircraft_id, :gufi,
                     :meter_fix, :scheduled_time, :actual_time, :sequence_number,
                     :delay_minutes, :arrival_runway, :flight_status, CAST(:extra_data AS JSONB))
                ON CONFLICT DO NOTHING
            """),
            {
                "received_at":      rec.get("received_at", datetime.now(timezone.utc)),
                "publication_type": rec.get("publication_type"),
                "airport":          rec.get("airport"),
                "aircraft_id":      rec.get("aircraft_id"),
                "gufi":             rec.get("gufi"),
                "meter_fix":        rec.get("meter_fix"),
                "scheduled_time":   rec.get("scheduled_time"),
                "actual_time":      rec.get("actual_time"),
                "sequence_number":  rec.get("sequence_number"),
                "delay_minutes":    rec.get("delay_minutes"),
                "arrival_runway":   rec.get("arrival_runway"),
                "flight_status":    rec.get("flight_status"),
                "extra_data":       extra_json,
            },
        )

    # ── TMIs ──────────────────────────────────────────────────────────────────

    def _upsert_tmi(self, session, rec: dict) -> None:
        extra = rec.get("extra_data")
        extra_json = json.dumps(extra) if extra else None

        session.execute(
            text("""
                INSERT INTO tbfm_tmis
                    (received_at, publication_type, tmi_type, airport,
                     program_name, start_time, end_time, arrival_rate, extra_data)
                VALUES
                    (:received_at, :publication_type, :tmi_type, :airport,
                     :program_name, :start_time, :end_time, :arrival_rate, CAST(:extra_data AS JSONB))
                ON CONFLICT (tmi_type, airport, start_time) DO UPDATE SET
                    end_time      = EXCLUDED.end_time,
                    arrival_rate  = EXCLUDED.arrival_rate,
                    extra_data    = EXCLUDED.extra_data,
                    updated_at    = NOW()
            """),
            {
                "received_at":      rec.get("received_at", datetime.now(timezone.utc)),
                "publication_type": rec.get("publication_type"),
                "tmi_type":         rec.get("tmi_type"),
                "airport":          rec.get("airport"),
                "program_name":     rec.get("program_name"),
                "start_time":       rec.get("start_time"),
                "end_time":         rec.get("end_time"),
                "arrival_rate":     rec.get("arrival_rate"),
                "extra_data":       extra_json,
            },
        )

    # ── Raw messages ──────────────────────────────────────────────────────────

    def _store_raw(self, session, rec: dict) -> None:
        raw = rec.get("raw_xml", b"")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        session.execute(
            text("""
                INSERT INTO tbfm_raw_messages (received_at, root_element, raw_xml, parse_error)
                VALUES (:received_at, :root_element, :raw_xml, :parse_error)
            """),
            {
                "received_at":  datetime.now(timezone.utc),
                "root_element": rec.get("root_element") or rec.get("root"),
                "raw_xml":      raw[:65535],   # cap to 64 KB
                "parse_error":  rec.get("parse_error"),
            },
        )
