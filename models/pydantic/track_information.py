from pydantic import BaseModel


class TrackInformationModel(BaseModel):
    aircraft_id: str
    gufi: str
    speed: int
    altitude: int
    latitude: str  # Update to string
    longitude: str  # Update to string
    time_at_position: str
    departure_airport: str
    arrival_airport: str
    airline: str
    aircraft_category: str
    user_category: str
