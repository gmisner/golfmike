# models/pydantic/fxa_updates.py

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class FxaUpdatesModel(BaseModel):
    id: Optional[int]
    aircraft_id: str
    update_time: datetime
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
