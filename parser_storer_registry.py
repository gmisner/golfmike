from functools import lru_cache

# ── Parsers ────────────────────────────────────────────────────────────────────
from parsers.flight_plan_parser import parse_flight_plan
from parsers.flight_sectors_parser import parse_flight_sectors
from parsers.status_parser import parse_status
from parsers.tmi_flight_list_parser import parse_tmi_flight_list
from parsers.track_information_parser import parse_track_information

# FDPS delta messages (flightModification / flightAmendment)
from parsers.flight_modify_parser import parse_flight_modify
from parsers.flight_plan_amendment_parser import parse_flight_plan_amendment

# TFM / NCSM message types
from parsers.arrival_information_parser import parse_arrival_information
from parsers.departure_information_parser import parse_departure_information
from parsers.beacon_code_parser import parse_beacon_code_information
from parsers.boundary_crossing_parser import parse_boundary_crossing_update
from parsers.flight_plan_cancellation_parser import parse_flight_plan_cancellation
from parsers.flight_plan_traffic_parser import parse_flight_plan_traffic
from parsers.flight_schedule_activate_parser import parse_flight_schedule_activate
from parsers.ncsm_flight_modify_parser import parse_ncsm_flight_modify
from parsers.ncsm_flight_route_parser import parse_flight_route
from parsers.ncsm_flight_times_parser import parse_flight_times
from parsers.ncsm_flight_control_parser import parse_flight_control
from parsers.oceanic_report_parser import parse_oceanic_report

# ── Storers ────────────────────────────────────────────────────────────────────
from storers.flight_plan_storer import store_flight_plan
from storers.flight_modify_storer import store_flight_modification
from storers.status_storer import store_status
from storers.tmi_flight_list_storer import store_tmi_flight_list
from storers.flight_sectors_storer import store_flight_sectors
from storers.track_information_storer import store_track_information

from storers.arrival_information_storer import store_arrival_information
from storers.departure_information_storer import store_departure_information
from storers.beacon_code_storer import store_beacon_code_updates
from storers.flight_cancellation_storer import store_flight_plan_cancellations
from storers.flight_plan_traffic_storer import store_flight_plan_traffic
from storers.route_assignment_storer import store_route_assignments
from storers.flight_times_storer import store_flight_times

# ── Registry ───────────────────────────────────────────────────────────────────
PARSERS = {
    # Core flight plan / tracking
    "TMI_FLIGHT_LIST": parse_tmi_flight_list,
    "FlightSectors": parse_flight_sectors,
    "trackInformation": parse_track_information,

    # FDPS delta messages — both casings
    "flightModification": parse_flight_modify,
    "flightAmendment": parse_flight_plan_amendment,
    "FlightAmendment": parse_flight_plan_amendment,

    # TFM / NCSM operational messages
    "arrivalInformation": parse_arrival_information,
    "departureInformation": parse_departure_information,
    "beaconCodeInformation": parse_beacon_code_information,
    "boundaryCrossingUpdate": parse_boundary_crossing_update,
    "flightPlanCancellation": parse_flight_plan_cancellation,
    "flightPlanTraffic": parse_flight_plan_traffic,
    "FlightScheduleActivate": parse_flight_schedule_activate,
    "FlightModify": parse_ncsm_flight_modify,
    "FlightRoute": parse_flight_route,
    "FlightTimes": parse_flight_times,
    "FlightControl": parse_flight_control,
    "oceanicReport": parse_oceanic_report,
}

STORERS = {
    # Core
    "TMI_FLIGHT_LIST": store_tmi_flight_list,
    "FlightSectors": store_flight_sectors,
    "trackInformation": store_track_information,

    # FDPS deltas
    "flightModification": store_flight_modification,
    "flightAmendment": store_flight_modification,
    "FlightAmendment": store_flight_modification,

    # TFM / NCSM
    "arrivalInformation": store_arrival_information,
    "departureInformation": store_departure_information,
    "beaconCodeInformation": store_beacon_code_updates,
    "flightPlanCancellation": store_flight_plan_cancellations,
    "flightPlanTraffic": store_flight_plan_traffic,
    "FlightScheduleActivate": store_route_assignments,
    "FlightModify": store_flight_plan_traffic,
    "FlightRoute": store_route_assignments,
    "FlightTimes": store_flight_times,
    # boundaryCrossingUpdate, FlightControl, oceanicReport — parsed but no DB table yet
}


def register_parser(msg_type, parser_func):
    PARSERS[msg_type] = parser_func
    get_parser.cache_clear()


def register_storer(msg_type, storer_func):
    STORERS[msg_type] = storer_func
    get_storer.cache_clear()


@lru_cache(maxsize=128)
def get_parser(msg_type):
    return PARSERS.get(msg_type)


@lru_cache(maxsize=128)
def get_storer(msg_type):
    return STORERS.get(msg_type)
