from typing import List
from lxml import etree
from models.pydantic.flight_sectors import FlightSectorsModel
from utils.logger import main_logger as logger

NAMESPACES = {
    "ds": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "fdm": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "nxce": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "nxcm": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns2": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns4": "urn:us:gov:dot:faa:atm:tfm:ficommondatatypes",
    "ns3": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "ns6": "http://www.fixm.aero/tfm/3.1",
    "ns5": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "ns8": "http://www.faa.aero/nas/3.1",
    "ns7": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "ns13": "urn:us:gov:dot:faa:atm:tfm:rapttimeline",
    "ns9": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2",
    "ns12": "urn:us:gov:dot:faa:atm:tfm:flowinformation",
    "ns11": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages",
    "ns10": "urn:us:gov:dot:faa:atm:tfm:tfmrequestreplytypes",
    "ns16": "http://www.fixm.aero/foundation/3.0",
    "ns15": "http://www.fixm.aero/base/3.0",
    "ns14": "http://www.fixm.aero/flight/3.0",
}


def parse_flight_sectors(xml_data: bytes) -> List[FlightSectorsModel]:
    """Parses airspace assignment XML data."""
    try:
        root = etree.fromstring(xml_data)
        flight_sectors = []

        for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
            aircraft_id = message.find(".//nxce:aircraftId", namespaces=NAMESPACES).text
            flight_ref = message.get("flightRef")
            dep_arpt = message.get("depArpt")
            arr_arpt = message.get("arrArpt")
            igtd = message.find(".//nxce:igtd", namespaces=NAMESPACES).text
            flight_traversal_data = message.find(
                ".//nxcm:flightTraversalData2", namespaces=NAMESPACES
            )

            fixes = []
            waypoints = []
            sectors = []
            airways = []
            centers = []

            if flight_traversal_data is not None:
                for fix in flight_traversal_data.findall(
                    ".//nxce:fix", namespaces=NAMESPACES
                ):
                    fixes.append(
                        {
                            "sequenceNumber": fix.get("sequenceNumber"),
                            "fix": fix.text,
                            "elapsedTime": fix.get("elapsedTime"),
                        }
                    )

                for waypoint in flight_traversal_data.findall(
                    ".//nxce:waypoint", namespaces=NAMESPACES
                ):
                    waypoints.append(
                        {
                            "sequenceNumber": waypoint.get("sequenceNumber"),
                            "latitudeDecimal": waypoint.get("latitudeDecimal"),
                            "longitudeDecimal": waypoint.get("longitudeDecimal"),
                            "elapsedTime": waypoint.get("elapsedTime"),
                        }
                    )

                for sector in flight_traversal_data.findall(
                    ".//nxce:sector", namespaces=NAMESPACES
                ):
                    sectors.append(
                        {
                            "sequenceNumber": sector.get("sequenceNumber"),
                            "sector": sector.text,
                            "elapsedEntryTime": sector.get("elapsedEntryTime"),
                        }
                    )

                for airway in flight_traversal_data.findall(
                    ".//nxce:airway", namespaces=NAMESPACES
                ):
                    airways.append(
                        {
                            "sequenceNumber": airway.get("sequenceNumber"),
                            "airway": airway.text,
                        }
                    )

                for center in flight_traversal_data.findall(
                    ".//nxce:center", namespaces=NAMESPACES
                ):
                    centers.append(
                        {
                            "sequenceNumber": center.get("sequenceNumber"),
                            "center": center.text,
                            "elapsedEntryTime": center.get("elapsedEntryTime"),
                        }
                    )

            flight_sectors.append(
                FlightSectorsModel(
                    aircraftId=aircraft_id,
                    flightRef=flight_ref,
                    depArpt=dep_arpt,
                    arrArpt=arr_arpt,
                    igtd=igtd,
                    fixes=fixes,
                    waypoints=waypoints,
                    sectors=sectors,
                    airways=airways,
                    centers=centers,
                )
            )

        return flight_sectors
    except Exception as e:
        logger.error(f"Error parsing Airspace Assignment Data: {e}", exc_info=True)
        return []
