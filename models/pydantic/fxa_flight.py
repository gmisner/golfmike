# models/pydantic/fxa_updates.py

from datetime import datetime
from dateutil.parser import isoparse
from pydantic import BaseModel, Field
from typing import Optional


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

    class Config:
        orm_mode = True


class FxaId(BaseModel):
    fcaId: str = Field(..., alias="fcaId")
    fcaName: str = Field(..., alias="fcaName")
    lastUpdate: datetime = Field(..., alias="lastUpdate")

    # Custom parser for 'lastUpdate' field (optional but recommended)
    @classmethod
    def _parse_last_update(cls, value: str) -> datetime:
        if value:
            return isoparse(value)
        else:
            return None  # Or handle the missing value differently
