from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from dateutil.parser import isoparse


class FlightDataType(BaseModel):
    flight: "FlightType" = Field(..., alias="flight")
    flightReference: Optional[str] = Field(None, alias="flightReference")
    status: Optional[str] = Field(None, alias="status")
    tmiFlightInfoList: "TmiFlightInfoListType" = Field(..., alias="tmiFlightInfoList")


class TmiFlightDataListType(BaseModel):
    flightData: List[FlightDataType] = Field(..., alias="flightData")


class FiMessageType(BaseModel):
    sensitivity: Optional[str] = Field(None, alias="@sensitivity")
    visDomain: Optional[str] = Field(None, alias="@visDomain")
    destinationCodes: Optional[str] = Field(None, alias="@destinationCodes")
    sourceFacility: Optional[str] = Field(None, alias="@sourceFacility")
    sourceTimeStamp: Optional[datetime] = Field(
        None, alias="@sourceTimeStamp", parser=isoparse
    )
    msgType: Optional[str] = Field(None, alias="@msgType")
    tmiFlightDataList: Optional[TmiFlightDataListType] = Field(
        None, alias="tmiFlightDataList"
    )

    class Config:
        xml_root_name = "fiMessage"  # Define the root element name
