from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.status import StatusModel
from utils.logger import main_logger as logger


def parse_status(status_data: etree.Element) -> Optional[StatusModel]:
    """
    parse_status _summary_

    Args:
        status_data (etree.Element): _description_

    Returns:
        Optional[StatusModel]: _description_
    """
    try:
        status_dict = {}

        # Extract attributes from status_data
        for key, value in status_data.attrib.items():
            status_dict[key] = value

        # Extract elements from status_data
        for element in status_data.iterchildren():
            tag = etree.QName(element).localname
            if tag == "artcc":
                # Handle artcc elements separately as they have attributes
                status_dict["artcc"] = [
                    {"center": c.text, "state": c.get("state")} for c in element
                ]
            else:
                status_dict[tag] = element.text

        # Convert datetime
        status_dict["time"] = isoparse(status_dict["time"])

        # Assuming 'time' and 'statusType' are used to create a unique 'id'
        status_dict["id"] = (
            f"{status_dict['time'].isoformat()}_{status_dict['statusType']}"
        )

        return StatusModel(**status_dict)
    except Exception as e:
        logger.error(f"Error parsing status: {e}", exc_info=True)
        return None
