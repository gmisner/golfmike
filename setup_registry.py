from parsers.tmi_flight_list_parser import parse_tmi_flight_list
from parsers.airspace_assignment_parser import parse_airspace_assignment
from storers.tmi_flight_list_storer import store_tmi_flight_list
from storers.airspace_assignment_storer import store_airspace_assignments
from parser_storer_registry import register_parser, register_storer


def setup_registry():
    register_parser("TMI_FLIGHT_LIST", parse_tmi_flight_list)
    register_storer("TMI_FLIGHT_LIST", store_tmi_flight_list)

    register_parser("FlightSectors", parse_airspace_assignment)
    register_storer("FlightSectors", store_airspace_assignments)

    # Register more parsers and storers as needed
