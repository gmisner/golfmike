from lxml import etree
from dateutil.parser import isoparse
from typing import Optional
from models.pydantic.track import TrackInformation
from utils.logger import main_logger as logger


def parse_track_information(
    track_info_element: etree.Element,
) -> Optional[TrackInformation]:
    """Parses trackInformation XML element into a TrackInformation model."""
    try:
        track_info_dict = {}
        for element in track_info_element.iterchildren():
            tag = etree.QName(element).localname
            if tag == "qualifiedAircraftId":
                for child in element.iterchildren():
                    child_tag = etree.QName(child).localname
                    if child_tag == "computerId":
                        for grand_child in child.iterchildren():
                            grand_child_tag = etree.QName(grand_child).localname
                            track_info_dict[grand_child_tag] = grand_child.text
                    track_info_dict[child_tag] = child.text
            elif tag == "reportedAltitude":
                for child in element.iterchildren():
                    track_info_dict["assignedAltitude"] = child.find(
                        "nxce:simpleAltitude", namespaces=NAMESPACES
                    ).text
            elif tag == "position":
                lat = element.find(
                    "nxce:latitude/nxce:latitudeDMS", namespaces=NAMESPACES
                )
                lon = element.find(
                    "nxce:longitude/nxce:longitudeDMS", namespaces=NAMESPACES
                )
                track_info_dict["latitude"] = (
                    f"{lat.get('degrees')}°{lat.get('minutes')}'{lat.get('seconds')}{lat.get('direction')}"
                )
                track_info_dict["longitude"] = (
                    f"{lon.get('degrees')}°{lon.get('minutes')}'{lon.get('seconds')}{lon.get('direction')}"
                )
            elif tag == "timeAtPosition":
                track_info_dict["timeAtPosition"] = isoparse(element.text)
            elif tag == "ncsmTrackData":
                eta = element.find("nxcm:eta", namespaces=NAMESPACES)
                if eta is not None:
                    track_info_dict["eta"] = isoparse(eta.get("timeValue"))
                rvsm_data = element.find("nxcm:rvsmData", namespaces=NAMESPACES)
                if rvsm_data is not None:
                    track_info_dict["rvsmCompliance"] = (
                        rvsm_data.get("currentCompliance") == "true"
                    )
            else:
                track_info_dict[tag] = element.text

        return TrackInformation(**track_info_dict)
    except Exception as e:
        logger.error(f"Error parsing trackInformation: {e}", exc_info=True)
        return None
