from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TrackInformationModel(BaseModel):
    aircraft_id: Optional[str]  # Aircraft identifier
    gufi: Optional[str]  # Globally unique flight identifier
    igtd: Optional[str] = None  # Initial gate departure time (from qualifiedAircraftId)
    speed: Optional[int]  # Speed of the aircraft
    altitude: int  # Altitude of the aircraft (default to 0 if not provided)
    latitude: Optional[str]  # Latitude in decimal format
    longitude: Optional[str]  # Longitude in decimal format
    time_at_position: Optional[str]  # Time at the current position
    departure_airport: str  # Departure airport code
    arrival_airport: str  # Arrival airport code
    airline: str  # Airline identifier
    aircraft_category: str  # Category of the aircraft (e.g., JET, TURBOPROP)
    user_category: str  # User category (e.g., COMMERCIAL, PRIVATE)
    flight_ref: Optional[str] = None  # fltdMessage flightRef
    source_facility: Optional[str] = None  # fltdMessage sourceFacility
    source_time_stamp: Optional[str] = None  # fltdMessage sourceTimeStamp
    computer_facility: Optional[str] = None  # computerId / facilityIdentifier
    computer_id_number: Optional[str] = None  # computerId / idNumber
    etd: Optional[str]  # Estimated time of departure
    eta: Optional[str]  # Estimated time of arrival
    diversion_indicator: Optional[str]  # Diversion indicator status
    rvsm_data: Optional[Dict[str, str]]  # RVSM data attributes
    next_position: Optional[Dict[str, str]]  # Next position with latitude and longitude
    fixes: List[Optional[str]]  # List of flight traversal fixes
    waypoints: List[
        Dict[str, Optional[str]]
    ]  # List of waypoints with latitude, longitude, elapsed time, sequence
    sectors: List[Optional[str]]  # List of sector names (ordered)
    sector_details: List[Dict[str, Optional[str]]] = Field(
        default_factory=list
    )  # sector name, sequence, elapsedEntryTime
    airways: List[str] = Field(default_factory=list)
    centers: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    star_route_name: Optional[str] = None
    star_route_type: Optional[str] = None
    star_transition_fix: Optional[str] = None
    route_arrival_fix_name: Optional[str] = None  # ncsmRouteData arrivalFixAndTime
    route_arrival_fix_time: Optional[str] = None
    route_of_flight: Optional[str]  # Route of flight description
    track_data: Optional[Dict[str, Any]]  # ncsmTrackData (fixes, ETA, nextEvent, etc.)
