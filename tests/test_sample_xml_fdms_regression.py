"""
Regression tests for Sample XML files: arrivalInformation, boundaryCrossingUpdate, oceanicReport.

These samples are schema-faithful fragments (not necessarily from a live broker dump) so we
can assert parser output without external data.
"""

import unittest
from pathlib import Path

from parsers.xml_namespaces import parse_swim_xml_root
from parsers.arrival_information_parser import parse_arrival_information
from parsers.boundary_crossing_parser import parse_boundary_crossing_update
from parsers.oceanic_report_parser import parse_oceanic_report
from swim_data_processor import parse_xml_to_pydantic
from utils.swim_message_audit import audit_swim_payload


def _root(name: str):
    path = Path(__file__).resolve().parents[1] / "Sample XML" / name
    return parse_swim_xml_root(path.read_text(encoding="utf-8"))


class TestArrivalInformationSample(unittest.TestCase):
    def test_parses_gufi_and_times(self):
        root = _root("arrivalInformation.xml")
        rows = parse_arrival_information(root)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.get("aircraft_id"), "SWA100")
        self.assertEqual(r.get("gufi"), "KSAMPLARV0001")
        self.assertEqual(r.get("time_of_arrival"), "2026-04-25T19:15:00Z")
        self.assertIn("19:20:00", r.get("eta_time") or "")

    def test_multiplexer_includes_msg_type(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "Sample XML"
            / "arrivalInformation.xml"
        ).read_text(encoding="utf-8")
        parts = parse_xml_to_pydantic(text)
        self.assertIsNotNone(parts)
        self.assertIn("arrivalInformation", [p[0] for p in parts or []])

    def test_audit_reports_full_pipeline(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "Sample XML"
            / "arrivalInformation.xml"
        ).read_text(encoding="utf-8")
        audit = audit_swim_payload(text)
        self.assertIsNone(audit.parse_error)
        by_type = {row.msg_type: row for row in audit.type_coverage}
        self.assertIn("arrivalInformation", by_type)
        self.assertTrue(by_type["arrivalInformation"].has_parser)
        self.assertTrue(by_type["arrivalInformation"].has_storer)


class TestBoundaryCrossingSample(unittest.TestCase):
    def test_parses_named_fix_and_time(self):
        root = _root("boundaryCrossingUpdate.xml")
        rows = parse_boundary_crossing_update(root)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.get("aircraft_id"), "AAL201")
        self.assertEqual(r.get("gufi"), "KSAMPLBND0002")
        self.assertEqual(r.get("boundary_fix"), "CHORD")
        self.assertIn("15:22:00", r.get("boundary_crossing_time") or "")
        self.assertIn("routeOfFlight", r.get("raw_payload") or "")
        self.assertIn("CHORD", r.get("raw_payload") or "")

    def test_audit_reports_full_pipeline(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "Sample XML"
            / "boundaryCrossingUpdate.xml"
        ).read_text(encoding="utf-8")
        audit = audit_swim_payload(text)
        self.assertIsNone(audit.parse_error)
        by_type = {row.msg_type: row for row in audit.type_coverage}
        self.assertIn("boundaryCrossingUpdate", by_type)
        self.assertTrue(by_type["boundaryCrossingUpdate"].has_parser)
        self.assertTrue(by_type["boundaryCrossingUpdate"].has_storer)


class TestOceanicReportSample(unittest.TestCase):
    def test_parses_gufi_and_speed(self):
        root = _root("oceanicReport.xml")
        rows = parse_oceanic_report(root)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.get("aircraft_id"), "BAW112")
        self.assertEqual(r.get("gufi"), "KSAMPLOCN0003")
        self.assertEqual(r.get("speed"), "480")
        snippet = r.get("reported_position_snippet") or ""
        self.assertIn("reportedPositionData", snippet)
        self.assertIn("latitudeDMS", snippet)
        self.assertIn("longitudeDMS", snippet)
        self.assertIn("2026-04-25T12:00:00Z", snippet)

    def test_audit_reports_full_pipeline(self):
        text = (
            Path(__file__).resolve().parents[1] / "Sample XML" / "oceanicReport.xml"
        ).read_text(encoding="utf-8")
        audit = audit_swim_payload(text)
        self.assertIsNone(audit.parse_error)
        by_type = {row.msg_type: row for row in audit.type_coverage}
        self.assertIn("oceanicReport", by_type)
        self.assertTrue(by_type["oceanicReport"].has_parser)
        self.assertTrue(by_type["oceanicReport"].has_storer)


if __name__ == "__main__":
    unittest.main()
