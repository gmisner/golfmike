from typing import List, Dict
from pydantic import BaseModel


class FlightSectorsModel(BaseModel):
    aircraftId: str
    flightRef: str
    depArpt: str
    arrArpt: str
    igtd: str
    fixes: List[Dict]
    waypoints: List[Dict]
    sectors: List[Dict]
    airways: List[Dict]
    centers: List[Dict]
