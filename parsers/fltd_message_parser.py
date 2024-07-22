from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.track import FltdMessage
from utils.logger import main_logger as logger

from .track_information_parser import parse_track_information

NAMESPACES = {
    "ns2": "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages",
    "ns3": "urn:us:gov:dot:faa:atm:tfm:flightdata",
    "ns4": "urn:us:gov:dot:faa:atm:tfm:ficommondatatypes",
    "ns5": "urn:us:gov:dot:faa:atm:tfm:tfmdataservice",
    "ns6": "http://www.fixm.aero/tfm/3.1",
    "ns7": "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements",
    "ns8": "http://www.faa.aero/nas/3.1",
    "ns9": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2",
    "ns10": "urn:us:gov:dot:faa:atm:tfm:tfmrequestreplytypes",
    "ns11": "urn:us:gov:dot:faa:atm:tfm:ficommonmessages",
    "ns12": "urn:us:gov:dot:faa:atm:tfm:flowinformation",
    "ns13": "urn:us:gov:dot:faa:atm:tfm:rapttimeline",
    "ns14": "http://www.fixm.aero/flight/3.0",
    "ns15": "http://www.fixm.aero/base/3.0",
    "ns16": "http://www.fixm.aero/foundation/3.0",
}


def parse_fltd_message(fltd_message: etree.Element) -> Optional[FltdMessage]:
    """Parses fltdMessage XML element into a FltdMessage model."""
    try:
        message_dict = {}
        for key, value in fltd_message.attrib.items():
            if key in ["cdmPart"]:
                message_dict[key] = value.lower() == "true"
            else:
                message_dict[key] = value

        track_info_element = fltd_message.find(
            "fdm:trackInformation", namespaces=NAMESPACES
        )
        if track_info_element is not None:
            track_information = parse_track_information(track_info_element)
            if track_information:
                message_dict["trackInformation"] = track_information

        # Convert datetimes
        for key in ["sourceTimeStamp"]:
            if key in message_dict:
                message_dict[key] = isoparse(message_dict[key])

        return FltdMessage(**message_dict)
    except Exception as e:
        logger.error(f"Error parsing fltdMessage: {e}", exc_info=True)
        return None
