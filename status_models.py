from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from dateutil.parser import isoparse


class StatusModel(BaseModel):
    id: str = Field(...)
    classification: str
    time: datetime = Field(..., parser=isoparse)
    statusType: str
    source: str
    artcc: Optional[List[dict]] = None  # List of dictionaries with 'center' and 'state'
    software: Optional[str] = None
    process: Optional[str] = None
    details: Optional[str] = None
    numberOfMsgs: Optional[int] = None
