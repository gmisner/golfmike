from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.flight_plan import FlightPlanModel
from utils.logger import main_logger as logger


def parse_flight_plan_amendment(
    amendment_data: etree.Element,
) -> Optional[FlightPlanModel]:
    """
    parse_flight_plan_amendment _summary_

    Args:
        amendment_data (etree.Element): _description_

    Returns:
        Optional[FlightPlanModel]: _description_
    """
    try:
        flight_plan_amendment_dict = {}

        for element in amendment_data.iterchildren():
            tag = etree.QName(element).localname
            if tag == "qualifiedAircraftId":
                for child in element.iterchildren():
                    child_tag = etree.QName(child).localname
                    if child_tag == "computerId":
                        for grand_child in child.iterchildren():
                            grand_child_tag = etree.QName(grand_child).localname
                            flight_plan_amendment_dict[grand_child_tag] = (
                                grand_child.text
                            )
                    flight_plan_amendment_dict[child_tag] = child.text

                for k, v in element.attrib.items():
                    flight_plan_amendment_dict[k] = v
            elif tag == "amendmentData":
                for child in element.iterchildren():
                    child_tag = etree.QName(child).localname
                    if child_tag == "newFlightAircraftSpecs":
                        for k, v in child.attrib.items():
                            flight_plan_amendment_dict[k] = v
                        flight_plan_amendment_dict[child_tag] = child.text
                    elif child_tag == "newSpeed":
                        for grand_child in child.iterchildren():
                            grand_child_tag = etree.QName(grand_child).localname
                            flight_plan_amendment_dict[grand_child_tag] = (
                                grand_child.text
                            )
                    elif child_tag == "newCoordinationTime":
                        for k, v in child.attrib.items():
                            flight_plan_amendment_dict[k] = v
                        flight_plan_amendment_dict[child_tag] = child.text
                    else:
                        flight_plan_amendment_dict[child_tag] = child.text
            else:
                flight_plan_amendment_dict[tag] = element.text

        # Convert datetimes
        for key in flight_plan_amendment_dict:
            if key.endswith("Time") or key == "igtd" or key == "lastUpdate":
                if flight_plan_amendment_dict[key]:
                    flight_plan_amendment_dict[key] = isoparse(
                        flight_plan_amendment_dict[key]
                    )

        # Add required fields to flight_plan_amendment_dict (you need to determine these based on your XML)
        # For example:
        flight_plan_amendment_dict["sourceId_00e"] = "some_source_id"
        flight_plan_amendment_dict["sourceTime_00e1"] = "some_source_time"
        flight_plan_amendment_dict["sourceSeqNo_00e2"] = "some_source_seq_no"
        flight_plan_amendment_dict["flightId_02a"] = flight_plan_amendment_dict[
            "aircraftId"
        ]
        flight_plan_amendment_dict["typeOfAircraft_03c"] = flight_plan_amendment_dict[
            "newFlightAircraftSpecs"
        ]
        # ... add other required fields ...

        return FlightPlanModel(**flight_plan_amendment_dict)
    except Exception as e:
        logger.error(f"Error parsing flight plan amendment: {e}", exc_info=True)
        return None
