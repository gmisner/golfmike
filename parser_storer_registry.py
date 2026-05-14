from parsers.flight_plan_parser import parse_flight_plan
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.status_parser import parse_status
from parsers.flight_modify_parser import parse_flight_modify
from parsers.flight_plan_amendment_parser import parse_flight_plan_amendment
from parsers.tmi_flight_list_parser import parse_tmi_flight_list
from storers.flight_plan_storer import store_flight_plan
from storers.flight_modify_storer import store_flight_modification
from storers.status_storer import store_status
from storers.tmi_flight_list_storer import store_tmi_flight_list
from storers.flight_sectors_storer import store_flight_sectors
from parsers.track_information_parser import parse_track_information
from storers.track_information_storer import store_track_information
from functools import lru_cache

PARSERS = {
    "TMI_FLIGHT_LIST": parse_tmi_flight_list,
    "FlightSectors": parse_flight_sectors,
    "trackInformation": parse_track_information,
    # Flight modification / amendment — both casing variants registered
    "flightModification": parse_flight_modify,
    "FlightModify": parse_flight_modify,
    "flightAmendment": parse_flight_plan_amendment,
    "FlightAmendment": parse_flight_plan_amendment,
}

STORERS = {
    "TMI_FLIGHT_LIST": store_tmi_flight_list,
    "FlightSectors": store_flight_sectors,
    "trackInformation": store_track_information,
    "flightModification": store_flight_modification,
    "FlightModify": store_flight_modification,
    "flightAmendment": store_flight_modification,
    "FlightAmendment": store_flight_modification,
}


def register_parser(msg_type, parser_func):
    PARSERS[msg_type] = parser_func


def register_storer(msg_type, storer_func):
    STORERS[msg_type] = storer_func


@lru_cache(maxsize=128)
def get_parser(msg_type):
    return PARSERS.get(msg_type)


@lru_cache(maxsize=128)
def get_storer(msg_type):
    return STORERS.get(msg_type)
