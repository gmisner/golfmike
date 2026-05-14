import unittest
from unittest.mock import patch

from parsers.nas_message_collection_parser import parse_nas_message_collection_xml
from storers.track_information_to_updates import convert_and_store_track_updates
from swim_data_processor import parse_xml_to_pydantic


NAS_NON_POSITION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ns5:MessageCollection
  xmlns:ns5="http://www.faa.aero/nas/3.0"
  xmlns:ns2="http://www.fixm.aero/base/3.0"
  xmlns:ns3="http://www.fixm.aero/flight/3.0"
  xmlns:ns4="http://www.fixm.aero/foundation/3.0">
  <message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns5:FlightMessageType">
    <flight xsi:type="ns5:NasFlightType" flightType="SCHEDULED" centre="ZLC" source="HU" system="ATL" timestamp="2026-04-26T05:42:14.283Z">
      <agreed>
        <route xsi:type="ns5:NasRouteType" nasRouteText="KDFW./.3529N/10002W..CUSGA.BGHRN3.KBIL/0621" initialFlightRules="IFR"/>
      </agreed>
      <arrival xsi:type="ns5:NasArrivalType" arrivalPoint="KBIL"/>
      <departure xsi:type="ns5:NasDepartureType" departurePoint="KDFW"/>
      <enRoute xsi:type="ns5:NasEnRouteType">
        <beaconCodeAssignment>
          <currentBeaconCode>0535</currentBeaconCode>
        </beaconCodeAssignment>
      </enRoute>
      <flightIdentification xsi:type="ns5:NasFlightIdentificationType" aircraftIdentification="ENY3937"/>
      <flightStatus xsi:type="ns5:NasFlightStatusType" fdpsFlightStatus="ACTIVE"/>
      <gufi codeSpace="urn:uuid">0d253a23-8903-4fda-aeef-3ad34c07a2ed</gufi>
      <operator>
        <operatingOrganization>
          <organization name="ENY"/>
        </operatingOrganization>
      </operator>
      <requestedAirspeed>
        <nasAirspeed uom="KNOTS">423.0</nasAirspeed>
      </requestedAirspeed>
      <coordination coordinationTime="2026-04-26T05:48:00Z" coordinationTimeHandling="E">
        <coordinationFix xsi:type="ns2:RelativePointType" fix="CZI">
          <distance uom="NAUTICAL_MILES">14.0</distance>
          <radial uom="DEGREES">289.0</radial>
        </coordinationFix>
      </coordination>
    </flight>
  </message>
</ns5:MessageCollection>
"""


class TestNasNonPositionIngest(unittest.TestCase):
    def test_parser_keeps_non_position_nas_flight(self) -> None:
        rows = parse_nas_message_collection_xml(NAS_NON_POSITION_XML)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.aircraft_id, "ENY3937")
        self.assertEqual(row.gufi, "0d253a23-8903-4fda-aeef-3ad34c07a2ed")
        self.assertIsNone(row.latitude)
        self.assertIsNone(row.longitude)
        self.assertEqual(row.speed, 423)
        self.assertEqual(
            row.track_data["nas_message_collection"]["flight_status"], "ACTIVE"
        )
        self.assertEqual(
            row.track_data["nas_message_collection"]["current_beacon_code"], "0535"
        )
        self.assertEqual(
            row.track_data["nas_message_collection"]["coordination_fix"], "CZI"
        )

    def test_pipeline_routes_non_position_nas_to_alerts(self) -> None:
        parsed_parts = parse_xml_to_pydantic(NAS_NON_POSITION_XML)
        self.assertIsNotNone(parsed_parts)
        self.assertEqual(parsed_parts[0][0], "NAS_MessageCollection")
        rows = parsed_parts[0][1]
        self.assertEqual(len(rows), 1)

        with patch(
            "storers.track_information_to_updates.store_track_updates"
        ) as mock_track_updates, patch(
            "storers.track_information_to_updates.store_swim_rows_as_flight_alerts"
        ) as mock_alerts, patch(
            "storers.track_information_to_updates.upsert_flight_operational_fields"
        ) as mock_upsert:
            convert_and_store_track_updates(rows)
            mock_track_updates.assert_not_called()
            mock_alerts.assert_called_once()
            mock_upsert.assert_called_once()
            args, _ = mock_alerts.call_args
            self.assertEqual(args[1], "NAS_MessageCollection")
            self.assertEqual(args[0][0]["aircraft_id"], "ENY3937")
            upsert_kwargs = mock_upsert.call_args.kwargs
            self.assertEqual(upsert_kwargs["fields"]["current_beacon_code"], "0535")
            self.assertEqual(upsert_kwargs["fields"]["fdps_flight_status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
