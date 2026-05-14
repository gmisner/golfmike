"""Multiplexed TFM parsing: one fltdMessage per parse path."""

import unittest
from pathlib import Path

from swim_data_processor import parse_xml_to_pydantic


class TestMultiplexFltdMessage(unittest.TestCase):
    def test_trackinformation_xml_has_many_fltd_messages(self):
        path = (
            Path(__file__).resolve().parents[1] / "Sample XML" / "trackinformation.xml"
        )
        text = path.read_text(encoding="utf-8")
        parts = parse_xml_to_pydantic(text)
        self.assertIsNotNone(parts)
        self.assertGreater(len(parts or []), 10)
        mtypes = [p[0] for p in parts or []]
        self.assertIn("trackInformation", mtypes)
        self.assertIn("departureInformation", mtypes)
        # Each tuple is (msgType, parsed)
        for _, data in parts or []:
            self.assertIsNotNone(data)
            if isinstance(data, list):
                self.assertLessEqual(
                    len(data), 1, "single-message root yields small lists"
                )

    def test_tmi_uses_first_msgtype_only(self):
        path = Path(__file__).resolve().parents[1] / "Sample XML" / "tmiflightlist.xml"
        text = path.read_text(encoding="utf-8")
        parts = parse_xml_to_pydantic(text)
        self.assertIsNotNone(parts)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0][0], "TMI_FLIGHT_LIST")


if __name__ == "__main__":
    unittest.main()
