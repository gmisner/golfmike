from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional


class ArtccModel(BaseModel):
    center: str
    state: str


class StatusModel(BaseModel):
    id: str
    classification: str
    time: datetime
    statusType: str
    source: str
    artcc: List[ArtccModel]
    software: Optional[str]
    process: Optional[str]
    details: Optional[str]
    numberOfMsgs: Optional[int]

    class Config:
        orm_mode = True
