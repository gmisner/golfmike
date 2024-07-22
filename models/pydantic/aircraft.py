from pydantic import BaseModel
from typing import Optional


class AircraftModel(BaseModel):
    """
    AircraftModel _summary_

    Args:
        BaseModel (_type_): _description_
    """

    id: Optional[int]
    aircraft_id: str
    gufi: Optional[str]
    flight_reference: Optional[str]
    status: Optional[str]

    class Config:
        orm_mode = True
