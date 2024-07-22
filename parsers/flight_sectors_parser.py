from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.flight_sectors import FlightSectorsModel
from utils.logger import main_logger as logger


def parse_flight_sectors(flight_data: etree.Element) -> Optional[FlightSectorsModel]:
    """
    parse_flight_sectors _summary_

    Args:
        flight_data (etree.Element): _description_

    Returns:
        Optional[FlightSectorsModel]: _description_
    """
    try:
        # Assuming FlightSectors data is at the root level of flight_data
        flight_sectors_data = {}

        # Extract attributes
        for key, value in flight_data.attrib.items():
            flight_sectors_data[key] = value

        # Extract child elements
        for element in flight_data.iterchildren():
            tag = etree.QName(element).localname
            flight_sectors_data[tag] = (
                element.text
            )  # You might need more complex logic here based on the child elements

        # Convert datetimes
        if "sourceTimeStamp" in flight_sectors_data:
            flight_sectors_data["sourceTimeStamp"] = isoparse(
                flight_sectors_data["sourceTimeStamp"]
            )

        return FlightSectorsModel(**flight_sectors_data)

    except Exception as e:
        logger.error(f"Error parsing Flight Sectors: {e}", exc_info=True)
        return None
