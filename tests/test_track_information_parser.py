"""Regression: DAL2226 in Sample XML/trackinformation.xml uses DMS for current position; nextEvent is different."""

import unittest
from pathlib import Path

from lxml import etree

from parsers.track_information_parser import (
    convert_dms_to_decimal,
    parse_track_information,
)


class TestTrackInformationDAL2226(unittest.TestCase):
    def test_dms_position_not_next_event(self):
        path = (
            Path(__file__).resolve().parents[1] / "Sample XML" / "trackinformation.xml"
        )
        root = etree.parse(str(path)).getroot()
        rows = parse_track_information(root)
        dal = [r for r in rows if r.aircraft_id == "DAL2226"]
        self.assertEqual(len(dal), 1)
        m = dal[0]

        lat_exp = convert_dms_to_decimal("44", "51", "38", "NORTH")
        lon_exp = convert_dms_to_decimal("093", "10", "07", "WEST")
        self.assertEqual(m.latitude, lat_exp)
        self.assertEqual(m.longitude, lon_exp)

        # nextEvent in message (not current position)
        ne_lat = 44.78563251857681
        ne_lon = -93.10782898642806
        self.assertNotAlmostEqual(float(m.latitude), ne_lat, places=5)
        self.assertNotAlmostEqual(float(m.longitude), ne_lon, places=5)

        td = m.track_data or {}
        ne = td.get("next_event") or {}
        if isinstance(ne, dict) and ne.get("latitude"):
            self.assertAlmostEqual(float(ne["latitude"]), ne_lat, places=5)
            self.assertAlmostEqual(float(ne["longitude"]), ne_lon, places=5)


if __name__ == "__main__":
    unittest.main()
