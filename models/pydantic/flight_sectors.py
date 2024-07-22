# models/pydantic/flight_sectors.py

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class FlightSectorsModel(BaseModel):
    id: Optional[int]
    aircraft_id: str
    sector_id: str
    entry_time: datetime
    exit_time: datetime
    duration: float
    entry_lat: float
    entry_lon: float
    exit_lat: float
    exit_lon: float

    class Config:
        orm_mode = True
