from pydantic import BaseModel
from typing import Optional, List, Dict


class TrackInformationModel(BaseModel):
    aircraft_id: Optional[str]  # Aircraft identifier
    gufi: Optional[str]  # Globally unique flight identifier
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
    etd: Optional[str]  # Estimated time of departure
    eta: Optional[str]  # Estimated time of arrival
    diversion_indicator: Optional[str]  # Diversion indicator status
    rvsm_data: Optional[Dict[str, str]]  # RVSM data attributes
    next_position: Optional[Dict[str, str]]  # Next position with latitude and longitude
    fixes: List[Optional[str]]  # List of flight traversal fixes
    waypoints: List[
        Dict[str, Optional[str]]
    ]  # List of waypoints with latitude, longitude, and elapsed time
    sectors: List[Optional[str]]  # List of sectors
    route_of_flight: Optional[str]  # Route of flight description
