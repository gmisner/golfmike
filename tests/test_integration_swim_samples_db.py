"""
Integration: parse_and_store_to_database against PostgreSQL.

Skipped when no DB is reachable (local runs without Postgres). CI provides Postgres
and runs init_db before unittest.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import List

from sqlalchemy import bindparam, text
from sqlalchemy.exc import OperationalError

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "Sample XML" / "Ingestable"


def _postgres_reachable() -> bool:
    try:
        from db_config import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


@unittest.skipUnless(
    _postgres_reachable(),
    "PostgreSQL not reachable (set POSTGRES_HOST/POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB)",
)
class TestSwimSampleIngestPostgres(unittest.TestCase):
    _gufis: List[str] = ["KSAMPLARV0001", "KSAMPLBND0002", "KSAMPLOCN0003"]

    @classmethod
    def _purge_sample_flights(cls) -> None:
        """Remove hub rows keyed by sample GUFIs (avoid deleting aircraft — other FKs)."""
        from db_config import SessionLocal

        session = SessionLocal()
        try:
            del_alerts = text("DELETE FROM flight_alerts WHERE gufi IN :g").bindparams(
                bindparam("g", expanding=True)
            )
            session.execute(del_alerts, {"g": cls._gufis})
            del_flights = text("DELETE FROM flights WHERE gufi IN :g").bindparams(
                bindparam("g", expanding=True)
            )
            session.execute(del_flights, {"g": cls._gufis})
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def setUpClass(cls) -> None:
        from db_config import init_db

        init_db()
        cls._purge_sample_flights()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._purge_sample_flights()

    def test_arrival_boundary_oceanic_round_trip(self) -> None:
        from db_config import SessionLocal
        from swim_data_processor import parse_and_store_to_database

        for name in (
            "arrivalInformation.xml",
            "boundaryCrossingUpdate.xml",
            "oceanicReport.xml",
        ):
            xml = (SAMPLE_DIR / name).read_text(encoding="utf-8")
            self.assertTrue(
                parse_and_store_to_database(xml),
                f"parse_and_store_to_database should succeed for {name}",
            )

        session = SessionLocal()
        try:
            row = session.execute(
                text(
                    """
                    SELECT current_status, scheduled_arrival IS NOT NULL AS has_arr
                    FROM flights WHERE gufi = :g
                    """
                ),
                {"g": "KSAMPLARV0001"},
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "COMPLETED")
            self.assertTrue(row[1])

            b = session.execute(
                text(
                    """
                    SELECT alert_type, alert_data->>'boundary_fix' AS fix
                    FROM flight_alerts
                    WHERE gufi = :g AND alert_type = :t
                    ORDER BY id DESC LIMIT 1
                    """
                ),
                {"g": "KSAMPLBND0002", "t": "SWIM_boundaryCrossingUpdate"},
            ).fetchone()
            self.assertIsNotNone(b)
            self.assertEqual(b[0], "SWIM_boundaryCrossingUpdate")
            self.assertEqual(b[1], "CHORD")

            o = session.execute(
                text(
                    """
                    SELECT alert_type, alert_data->>'speed' AS spd
                    FROM flight_alerts
                    WHERE gufi = :g AND alert_type = :t
                    ORDER BY id DESC LIMIT 1
                    """
                ),
                {"g": "KSAMPLOCN0003", "t": "SWIM_oceanicReport"},
            ).fetchone()
            self.assertIsNotNone(o)
            self.assertEqual(o[0], "SWIM_oceanicReport")
            self.assertEqual(o[1], "480")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
