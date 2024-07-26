# setup_registry.py

from parser_storer_registry import register_parser, register_storer
from parsers.tmi_flight_list_parser import parse_tmi_flight_list
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.track_information_parser import parse_track_information
from storers.tmi_flight_list_storer import store_tmi_flight_list
from storers.flight_sectors_storer import store_flight_sectors
from storers.track_information_storer import store_track_information


def setup_registry():
    register_parser("TMI_FLIGHT_LIST", parse_tmi_flight_list)
    register_storer("TMI_FLIGHT_LIST", store_tmi_flight_list)

    register_parser("FlightSectors", parse_flight_sectors)
    register_storer("FlightSectors", store_flight_sectors)

    register_parser("trackInformation", parse_track_information)
    register_storer("trackInformation", store_track_information)
