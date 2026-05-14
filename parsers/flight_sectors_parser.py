from typing import List
from lxml import etree
from models.pydantic.flight_sectors import FlightSectorsModel
from parsers.xml_namespaces import SWIM_NAMESPACES as NAMESPACES
from utils.logger import main_logger as logger


def parse_flight_sectors(root: etree._Element) -> List[FlightSectorsModel]:
    """Parses airspace assignment XML from an already-parsed root."""
    try:
        flight_sectors = []

        for message in root.findall(".//fdm:fltdMessage", namespaces=NAMESPACES):
            _acid_elem = message.find(".//nxce:aircraftId", namespaces=NAMESPACES)
            _igtd_elem = message.find(".//nxce:igtd", namespaces=NAMESPACES)

            aircraft_id = _acid_elem.text if _acid_elem is not None else None
            igtd = _igtd_elem.text if _igtd_elem is not None else None

            if not aircraft_id:
                logger.warning("fltdMessage missing aircraftId — skipping")
                continue

            flight_ref = message.get("flightRef")
            dep_arpt = message.get("depArpt")
            arr_arpt = message.get("arrArpt")
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
