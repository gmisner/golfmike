from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TrackInformation(BaseModel):
    aircraftId: str
    computerId: str
    facilityIdentifier: str
    idNumber: str
    gufi: str
    igtd: datetime
    departurePoint: str
    arrivalPoint: str
    speed: int
    assignedAltitude: str
    latitude: str
    longitude: str
    timeAtPosition: datetime
    eta: Optional[datetime]
    rvsmCompliance: bool


class FltdMessage(BaseModel):
    sourceTimeStamp: datetime
    trackInformation: TrackInformation
    cdmPart: Optional[bool]
    # Add other necessary fields
