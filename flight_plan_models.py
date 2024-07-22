from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from dateutil.parser import isoparse


class FlightPlanModel(BaseModel):
    id: str = Field(..., alias="gufi")  # Assuming gufi is unique
    sourceId_00e: str = Field(..., alias="sourceId_00e")
    sourceTime_00e1: str = Field(..., alias="sourceTime_00e1")
    sourceSeqNo_00e2: str = Field(..., alias="sourceSeqNo_00e2")
    flightId_02a: str = Field(..., alias="flightId_02a")
    computerId_02d: Optional[str] = Field(None, alias="computerId_02d")
    eramGufi_316a: Optional[str] = Field(None, alias="eramGufi_316a")
    eramGufi_316aNum: Optional[int] = Field(None, alias="eramGufi_316aNum")
    eramGufi_316aDT: Optional[datetime] = Field(
        None, alias="eramGufi_316aDT", parser=isoparse
    )
    sspId_167a: Optional[str] = Field(None, alias="sspId_167a")
    numberOfAircraft_03a: Optional[str] = Field(None, alias="numberOfAircraft_03a")
    typeOfAircraft_03c: str = Field(..., alias="typeOfAircraft_03c")
    airborneEquip_03e: Optional[str] = Field(None, alias="airborneEquip_03e")
    beaconCode_04a: Optional[str] = Field(None, alias="beaconCode_04a")
    externalBeaconCode_04b: Optional[str] = Field(None, alias="externalBeaconCode_04b")
    trueAirSpeed_05a: Optional[str] = Field(None, alias="trueAirSpeed_05a")
    machSpeed_05c: Optional[str] = Field(None, alias="machSpeed_05c")
    classifiedSpeed_05d: Optional[str] = Field(None, alias="classifiedSpeed_05d")
    coordFix_06a: str = Field(..., alias="coordFix_06a")
    coordStatusTime_07d: str = Field(..., alias="coordStatusTime_07d")
    coordStatus_07d1: str = Field(..., alias="coordStatus_07d1")
    coordTime_07d2: datetime = Field(..., alias="coordTime_07d2", parser=isoparse)
    delayTime_07e: Optional[str] = Field(None, alias="delayTime_07e")
    assignedAlt_08a: Optional[str] = Field(None, alias="assignedAlt_08a")
    assignedAlt_08b: Optional[str] = Field(None, alias="assignedAlt_08b")
    assignedAlt_08c: Optional[str] = Field(None, alias="assignedAlt_08c")
    assignedAlt_08d: Optional[str] = Field(None, alias="assignedAlt_08d")
    assignedAlt_08e: Optional[str] = Field(None, alias="assignedAlt_08e")
    assignedAlt_08f: Optional[str] = Field(None, alias="assignedAlt_08f")
    assignedAlt_08g: Optional[str] = Field(None, alias="assignedAlt_08g")
    assignedAlt_08h: Optional[str] = Field(None, alias="assignedAlt_08h")
    requestedAlt_09a: Optional[str] = Field(None, alias="requestedAlt_09a")
    requestedAlt_09b: Optional[str] = Field(None, alias="requestedAlt_09b")
    requestedAlt_09c: Optional[str] = Field(None, alias="requestedAlt_09c")
    requestedAlt_09d: Optional[str] = Field(None, alias="requestedAlt_09d")
    requestedAlt_09e: Optional[str] = Field(None, alias="requestedAlt_09e")
    requestedAlt_09f: Optional[str] = Field(None, alias="requestedAlt_09f")
    requestedAlt_09g: Optional[str] = Field(None, alias="requestedAlt_09g")
    flightPlanRoute_10a: str = Field(..., alias="flightPlanRoute_10a")
    departurePoint_26a: str = Field(..., alias="departurePoint_26a")
    destination_27a: str = Field(..., alias="destination_27a")
    # ... other fields from T_flightPlan ...
