"""
Synthetic FlightTimes XML: proves parse_flight_times + multiplexer without broker data.

The fixture is intentionally small. It does not need to be wire-valid end-to-end; it only
needs to use the same element names/namespaces our parser expects so we catch regressions
when those expectations change.
"""

import unittest
from pathlib import Path

from parsers.xml_namespaces import parse_swim_xml_root
from parsers.ncsm_flight_times_parser import parse_flight_times
from swim_data_processor import parse_xml_to_pydantic


class TestSyntheticFlightTimes(unittest.TestCase):
    def test_parse_flight_times_extracts_gufi_and_ctd(self):
        path = (
            Path(__file__).resolve().parent / "fixtures" / "synthetic_flight_times.xml"
        )
        root = parse_swim_xml_root(path.read_text(encoding="utf-8"))
        rows = parse_flight_times(root)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.get("gufi"), "KSYNTHFT0001")
        self.assertEqual(r.get("aircraft_id"), "TST123")
        self.assertIn("2026-04-25T11:05:00Z", (r.get("ctd") or ""))
        self.assertIn("2026-04-25T19:25:00Z", (r.get("cta") or ""))

    def test_multiplexer_sees_flight_times(self):
        path = (
            Path(__file__).resolve().parent / "fixtures" / "synthetic_flight_times.xml"
        )
        text = path.read_text(encoding="utf-8")
        parts = parse_xml_to_pydantic(text)
        self.assertIsNotNone(parts)
        mtypes = [p[0] for p in parts or []]
        self.assertIn("FlightTimes", mtypes)


if __name__ == "__main__":
    unittest.main()
