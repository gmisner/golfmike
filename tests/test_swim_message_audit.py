"""Unit tests for SWIM message type audit and WGS-84 checks."""

import unittest
from pathlib import Path

from utils.geo_validation import validate_wgs84_lat_lon
from utils.swim_message_audit import (
    audit_swim_payload,
    format_audit_report,
    registry_gap_summary,
)

NAS_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<MessageCollection xmlns="http://www.faa.aero/nas/3.0">
  <message></message>
</MessageCollection>
"""

MULTI_MSGTYPE = """<?xml version="1.0" encoding="UTF-8"?>
<ds:tfmDataService xmlns:ds="urn:us:gov:dot:faa:atm:tfm:tfmdataservice"
  xmlns:fdm="urn:us:gov:dot:faa:atm:tfm:flightdata">
  <fltdOutput>
   <fdm:fltdMessage msgType="trackInformation" />
   <fdm:fltdMessage msgType="FlightTimes" />
  </fltdOutput>
</ds:tfmDataService>
"""


class TestWgs84(unittest.TestCase):
    def test_valid(self):
        ok, err = validate_wgs84_lat_lon("44.5", "-93.1")
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_lat_out(self):
        ok, err = validate_wgs84_lat_lon(91, 0)
        self.assertFalse(ok)
        self.assertIn("latitude", err)


class TestSwimMessageAudit(unittest.TestCase):
    def test_nas_message_collection_routes_to_virtual_key(self):
        a = audit_swim_payload(NAS_MINIMAL)
        self.assertIsNone(a.parse_error)
        self.assertTrue(a.is_nas_message_collection)
        self.assertEqual(a.processor_would_use_msg_type, "NAS_MessageCollection")
        self.assertTrue(a.processor_routing_has_full_pipeline)

    def test_sample_trackinformation(self):
        path = (
            Path(__file__).resolve().parents[1] / "Sample XML" / "trackinformation.xml"
        )
        a = audit_swim_payload(path.read_text(encoding="utf-8"))
        self.assertIsNone(a.parse_error)
        self.assertFalse(a.is_nas_message_collection)
        self.assertIn("trackInformation", a.fltd_message_types)
        self.assertTrue(a.processor_routing_has_full_pipeline)
        for row in a.type_coverage:
            if row.msg_type == "trackInformation":
                self.assertTrue(row.has_parser and row.has_storer)

    def test_multi_fltdMessage_warns_in_report(self):
        a = audit_swim_payload(MULTI_MSGTYPE)
        self.assertIsNone(a.parse_error)
        rpt = format_audit_report(a)
        self.assertIn("Multiple fltdMessage", rpt)
        by_type = {row.msg_type: row for row in a.type_coverage}
        self.assertIn("FlightTimes", by_type)
        self.assertTrue(by_type["FlightTimes"].has_parser)
        self.assertTrue(by_type["FlightTimes"].has_storer)

    def test_xsd_gaps_finds_unregistered_tfm_types(self):
        extra, _missing = registry_gap_summary()
        self.assertEqual(
            extra,
            [],
            "Every FlightData.xsd messageType value should have a PARSERS entry",
        )
        self.assertNotIn("trackInformation", extra)


if __name__ == "__main__":
    unittest.main()
