# parser_storer_registry.py

from parsers.flight_plan_parser import parse_flight_plan
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.track_information_parser import parse_track_information
from parsers.fltd_message_parser import parse_fltd_message
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.status_parser import parse_status
from parsers.flight_modify_parser import parse_flight_modify
from parsers.flight_plan_amendment_parser import parse_flight_plan_amendment
from parsers.tmi_flight_list_parser import parse_tmi_flight_list
from storers.flight_plan_storer import store_flight_plan
from storers.track_storer import store_track
from storers.fltd_message_storer import store_fltd_message
from storers.status_storer import store_status
from storers.tmi_flight_list_storer import store_tmi_flight_list
from storers.flight_sectors_storer import store_flight_sectors

# A dictionary to store parsers based on message type
PARSERS = {
    "TMI_FLIGHT_LIST": parse_tmi_flight_list,
    "FlightSectors": parse_flight_sectors,
    # Add other message types and their parsers here
}

# A dictionary to store storers based on message type
STORERS = {
    "TMI_FLIGHT_LIST": store_tmi_flight_list,
    "FlightSectors": store_flight_sectors,
    # Add other message types and their parsers here
}


def register_parser(msg_type, parser_func):
    """Registers a parser function for a given message type."""
    PARSERS[msg_type] = parser_func


def get_parser(msg_type):
    """Retrieves the parser function for a given message type."""
    return PARSERS.get(msg_type)


def register_storer(msg_type, storer_func):
    """Registers a storer function for a given message type."""
    STORERS[msg_type] = storer_func


def get_storer(msg_type):
    """Retrieves the storer function for a given message type."""
    return STORERS.get(msg_type)
