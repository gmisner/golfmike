# models/pydantic/tmi_updates.py

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TmiUpdatesModel(BaseModel):
    id: Optional[int]
    aircraft_id: str
    update_time: datetime
    update_type: str
    last_update_time: datetime
    fca_id: str

    class Config:
        from_attributes = True
