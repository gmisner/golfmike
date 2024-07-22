from pydantic import BaseModel, Field
from typing import List, Optional


class FlightDataType(BaseModel):
    aircraftId: Optional[str]
    gufi: Optional[str]
    igtd: Optional[str]
    departurePoint: Optional[str]
    arrivalPoint: Optional[str]
    flightReference: Optional[str]
    status: Optional[str]


class FxaFlight(BaseModel):
    fcaId: Optional[str]
    fcaName: Optional[str]
    lastUpdate: Optional[str]
    bentryTm: Optional[str]
    createTm: Optional[str]
    eentryTm: Optional[str]
    entryTm: Optional[str]
    exitTm: Optional[str]
    extendedExitTm: Optional[str]
    ientryTm: Optional[str]
    oentryTm: Optional[str]
    entryLat: Optional[str]
    entryLon: Optional[str]
    entryHeading: Optional[str]
    exitInd: Optional[str]


class FxaFlightData(BaseModel):
    fxaFlight: List[FxaFlight]


class Tmi(BaseModel):
    updateType: Optional[str]
    lastUpdateTime: Optional[str]
    fcaId: Optional[str]


class TmiFlightInfoList(BaseModel):
    tmi: Optional[Tmi]
    fxaFlightData: Optional[FxaFlightData]


class TmiFlightListModel(BaseModel):
    flight: List[FlightDataType]
    tmiFlightInfoList: Optional[TmiFlightInfoList]
