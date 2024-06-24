from typing import Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime


class FxaId(BaseModel):
    fcaId: str = Field(..., alias="fcaId")
    fcaName: str = Field(..., alias="fcaName")
    lastUpdate: str = Field(..., alias="lastUpdate")


class Tmi(BaseModel):
    updateType: str = Field(..., alias="updateType")
    lastUpdateTime: str = Field(..., alias="lastUpdateTime")
    fcaId: Optional[str]


class FxaFlight(BaseModel):
    fxaId: Optional[FxaId]
    bentryTm: Optional[Union[datetime, str]] = Field(None, alias="bentryTm")
    createTm: Optional[Union[datetime, str]] = Field(None, alias="createTm")
    eentryTm: Optional[Union[datetime, str]] = Field(None, alias="eentryTm")
    entryTm: Optional[Union[datetime, str]] = Field(None, alias="entryTm")
    exitTm: Optional[Union[datetime, str]] = Field(None, alias="exitTm")
    extendedExitTm: Optional[Union[datetime, str]] = Field(None, alias="extendedExitTm")
    ientryTm: Optional[Union[datetime, str]] = Field(None, alias="ientryTm")
    oentryTm: Optional[Union[datetime, str]] = Field(None, alias="oentryTm")
    entryLat: Optional[str]
    entryLon: Optional[str]
    entryHeading: Optional[str]
    exitInd: Optional[str]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class FlightSectorsModel(BaseModel):
    id: str
    sensitivity: Optional[str]
    sourceFacility: Optional[str]
    sourceTimeStamp: Optional[datetime] = Field(None, alias="sourceTimeStamp")
    msgType: Optional[str]
    aircraftId: Optional[str]
    gufi: Optional[str]
    departurePoint: Optional[dict] = Field(None, alias="departurePoint")
    arrivalPoint: Optional[dict] = Field(None, alias="arrivalPoint")
    sectorDesignator: Optional[str] = Field(None, alias="sectorDesignator")
    sectorEntryTime: Optional[datetime] = Field(None, alias="sectorEntryTime")
    sectorExitTime: Optional[datetime] = Field(None, alias="sectorExitTime")
    entryPoint: Optional[dict] = Field(None, alias="entryPoint")
    exitPoint: Optional[dict] = Field(None, alias="exitPoint")
    crossingAltitude: Optional[float] = Field(None, alias="crossingAltitude")
    crossingSpeed: Optional[int] = Field(None, alias="crossingSpeed")
    flightLevel: Optional[str] = Field(None, alias="flightLevel")
    routeOfFlight: Optional[str] = Field(None, alias="routeOfFlight")
    trajectory: Optional[List[dict]] = Field(None, alias="trajectory")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TmiFlightListModel(BaseModel):
    id: str
    sensitivity: Optional[str]
    visDomain: Optional[str]
    destinationCodes: Optional[str]
    sourceFacility: Optional[str]
    sourceTimeStamp: Optional[datetime] = Field(None, alias="sourceTimeStamp")
    msgType: Optional[str]
    aircraftId: Optional[str]
    gufi: Optional[str]
    igtd: Optional[datetime] = Field(None, alias="igtd")
    flightReference: Optional[str]
    status: Optional[str]
    tmiFlightInfoList: Optional[List[Tmi]] = Field(None, alias="tmiFlightInfoList")
    fxaFlightData: Optional[List[FxaFlight]] = Field(None, alias="fxaFlightData")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class Airport(BaseModel):
    airport: str


class AssignedAltitude(BaseModel):
    simpleAltitude: str


class ReportedAltitude(BaseModel):
    assignedAltitude: AssignedAltitude


class LatitudeDMS(BaseModel):
    degrees: int
    direction: str
    minutes: int
    seconds: Optional[int]


class LongitudeDMS(BaseModel):
    degrees: int
    direction: str
    minutes: int
    seconds: Optional[int]


class Position(BaseModel):
    latitude: LatitudeDMS
    longitude: LongitudeDMS


class PlannedPositionData(BaseModel):
    planNumber: int = Field(..., alias="planNumber")
    position: Position
    altitude: int
    time: Union[datetime, str]


class ReportedPositionData(BaseModel):
    position: Position
    altitude: int
    time: Union[datetime, str]


class Eta(BaseModel):
    etaType: str = Field(..., alias="etaType")
    timeValue: Union[datetime, str]


class RvsmData(BaseModel):
    currentCompliance: bool = Field(..., alias="currentCompliance")
    equipped: bool
    futureCompliance: bool = Field(..., alias="futureCompliance")


class ArrivalFixAndTime(BaseModel):
    arrTime: Union[datetime, str]
    fixName: str = Field(..., alias="fixName")


class DepartureFixAndTime(BaseModel):
    arrTime: Union[datetime, str]
    fixName: str = Field(..., alias="fixName")


class NextEvent(BaseModel):
    latitudeDecimal: float = Field(..., alias="latitudeDecimal")
    longitudeDecimal: float = Field(..., alias="longitudeDecimal")


class NcsmTrackData(BaseModel):
    eta: Optional[Eta]
    rvsmData: Optional[RvsmData] = Field(None, alias="rvsmData")
    arrivalFixAndTime: Optional[ArrivalFixAndTime] = Field(
        None, alias="arrivalFixAndTime"
    )
    departureFixAndTime: Optional[DepartureFixAndTime] = Field(
        None, alias="departureFixAndTime"
    )
    nextEvent: Optional[NextEvent] = Field(None, alias="nextEvent")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class TrackInformationModel(BaseModel):
    id: str
    sensitivity: Optional[str]
    sourceFacility: Optional[str]
    sourceTimeStamp: Optional[datetime] = Field(None, alias="sourceTimeStamp")
    msgType: Optional[str]
    aircraftId: Optional[str]
    gufi: Optional[str]
    igtd: Optional[datetime] = Field(None, alias="igtd")
    departurePoint: Optional[Airport] = Field(None, alias="departurePoint")
    arrivalPoint: Optional[Airport] = Field(None, alias="arrivalPoint")
    speed: Optional[int] = Field(None, alias="speed")
    reportedAltitude: Optional[ReportedAltitude] = Field(None, alias="reportedAltitude")
    position: Optional[Position] = Field(None, alias="position")
    timeAtPosition: Optional[datetime] = Field(None, alias="timeAtPosition")
    ncsmTrackData: Optional[NcsmTrackData] = Field(None, alias="ncsmTrackData")
    ncsmRouteData: Optional[dict] = Field(None, alias="ncsmRouteData")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class OceanicReportModel(BaseModel):
    id: str
    sensitivity: Optional[str]
    sourceFacility: Optional[str]
    sourceTimeStamp: Optional[datetime] = Field(None, alias="sourceTimeStamp")
    msgType: Optional[str]
    aircraftId: Optional[str]
    gufi: Optional[str]
    igtd: Optional[datetime] = Field(None, alias="igtd")
    departurePoint: Optional[Airport] = Field(None, alias="departurePoint")
    arrivalPoint: Optional[Airport] = Field(None, alias="arrivalPoint")
    speed: Optional[int] = Field(None, alias="speed")
    plannedPositionData: Optional[List[PlannedPositionData]] = Field(
        None, alias="plannedPositionData"
    )
    reportedPositionData: Optional[ReportedPositionData] = Field(
        None, alias="reportedPositionData"
    )
    ncsmTrackData: Optional[NcsmTrackData] = Field(None, alias="ncsmTrackData")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class Sector(BaseModel):
    name: Optional[str]
    sequenceNumber: Optional[int]
    elapsedEntryTime: Optional[int]


class FlightSectorsModel(BaseModel):
    id: str
    sensitivity: Optional[str]
    sourceFacility: Optional[str]
    sourceTimeStamp: Optional[datetime] = Field(None, alias="sourceTimeStamp")
    msgType: Optional[str]
    aircraftId: Optional[str]
    gufi: Optional[str]
    departurePoint: Optional[Airport] = Field(None, alias="departurePoint")
    arrivalPoint: Optional[Airport] = Field(None, alias="arrivalPoint")
    sectorDesignator: Optional[str] = Field(None, alias="sectorDesignator")
    sectorEntryTime: Optional[datetime] = Field(None, alias="sectorEntryTime")
    sectorExitTime: Optional[datetime] = Field(None, alias="sectorExitTime")
    entryPoint: Optional[dict] = Field(None, alias="entryPoint")
    exitPoint: Optional[dict] = Field(None, alias="exitPoint")
    crossingAltitude: Optional[float] = Field(None, alias="crossingAltitude")
    crossingSpeed: Optional[int] = Field(None, alias="crossingSpeed")
    flightLevel: Optional[str] = Field(None, alias="flightLevel")
    routeOfFlight: Optional[str] = Field(None, alias="routeOfFlight")
    trajectory: Optional[List[Sector]] = Field(None, alias="trajectory")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
