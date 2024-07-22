from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.flight_plan import FlightPlanModel
from utils.logger import main_logger as logger


def parse_flight_modify(flight_modify_data: etree.Element) -> Optional[FlightPlanModel]:
    """
    parse_flight_modify _summary_

    Args:
        flight_modify_data (etree.Element): _description_

    Returns:
        Optional[FlightPlanModel]: _description_
    """
    try:
        flight_modify_data = flight_modify_data.find(
            "nxcm:airlineData", namespaces=NAMESPACES
        )
        flight_modify_dict = {}

        for element in flight_modify_data.iterchildren():
            tag = etree.QName(element).localname
            if tag == "flightStatusAndSpec":
                for child in element.iterchildren():
                    child_tag = etree.QName(child).localname
                    if child_tag == "aircraftSpecification":
                        for k, v in child.attrib.items():
                            flight_modify_dict[k] = v
                    flight_modify_dict[child_tag] = child.text
            elif tag == "flightTimeData":
                for k, v in element.attrib.items():
                    flight_modify_dict[k] = v
            elif tag == "arrivalFixAndTime":
                flight_modify_dict["arrivalFixName"] = element.get("@fixName")
                flight_modify_dict["arrivalFixTime"] = element.get("@arrTime")
            else:
                flight_modify_dict[tag] = element.text

        # Convert datetimes
        for key in flight_modify_dict:
            if (
                key.endswith("Time")
                or key == "igtd"
                or key == "lastUpdate"
                or key == "arrivalFixTime"
            ):
                if flight_modify_dict[key]:
                    flight_modify_dict[key] = isoparse(flight_modify_dict[key])

        # Add required fields to flight_modify_dict (you need to determine these based on your XML)
        # For example:
        flight_modify_dict["sourceId_00e"] = "some_source_id"
        flight_modify_dict["sourceTime_00e1"] = "some_source_time"
        flight_modify_dict["sourceSeqNo_00e2"] = "some_source_seq_no"
        flight_modify_dict["flightId_02a"] = flight_modify_dict["aircraftId"]
        flight_modify_dict["typeOfAircraft_03c"] = flight_modify_dict["aircraftModel"]
        # ... add other required fields ...

        return FlightPlanModel(**flight_modify_dict)
    except Exception as e:
        logger.error(f"Error parsing flight modify: {e}", exc_info=True)
        return None
