# models/pydantic/tmi_flight_list.py

from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class FxaFlightModel(BaseModel):
    fcaId: Optional[str] = None
    fcaName: Optional[str] = None
    lastUpdate: Optional[str] = None
    bentryTm: Optional[str] = None
    createTm: Optional[str] = None
    eentryTm: Optional[str] = None
    entryTm: Optional[str] = None
    exitTm: Optional[str] = None
    extendedExitTm: Optional[str] = None
    ientryTm: Optional[str] = None
    oentryTm: Optional[str] = None
    entryLat: Optional[float] = None
    entryLon: Optional[float] = None
    entryHeading: Optional[int] = None
    exitInd: Optional[str] = None

    class Config:
        from_attributes = True


class TMIFlightModel(BaseModel):
    """Model for TMI information"""
    update_type: Optional[str] = None
    last_update_time: Optional[str] = None
    fca_id: Optional[str] = None

    class Config:
        from_attributes = True


class TMIFlightListModel(BaseModel):
    aircraft_id: Optional[str] = None
    gufi: Optional[str] = None
    igtd: Optional[str] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    flight_reference: Optional[str] = None
    status: Optional[str] = None
    fxa_flights: List[Dict[str, Any]] = []
    tmi_info: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True
