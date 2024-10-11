# models/pydantic/tmi_flight_list.py

from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class FxaFlightModel(BaseModel):
    id: Optional[int]
    aircraft_id: str
    update_time: datetime
    fxaId: str
    fcaId: str
    fcaName: str
    lastUpdate: datetime
    bentryTm: datetime
    createTm: datetime
    eentryTm: datetime
    entryTm: datetime
    exitTm: datetime
    extendedExitTm: datetime
    ientryTm: datetime
    oentryTm: datetime
    entryLat: float
    entryLon: float
    entryHeading: int
    exitInd: str


class TMIFlightListModel(BaseModel):
    aircraft_id: str
    gufi: str
    igtd: datetime
    departure_airport: str
    arrival_airport: str
    fxa_flights: List[FxaFlightModel] = []

    class Config:
        from_attributes = True
