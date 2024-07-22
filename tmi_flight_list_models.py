from datetime import datetime
from typing import List, Optional
from pydantic_xml import BaseXmlModel, element
from dateutil.parser import isoparse


class PointType(BaseXmlModel):
    airport: Optional[str] = element(default=None)

    class Config:
        xml_root_name = "departurePoint"


class FlightType(BaseXmlModel):
    aircraftId: Optional[str] = element(default=None)
    gufi: Optional[str] = element(default=None)
    igtd: Optional[datetime] = element(default=None, parser=isoparse)
    departurePoint: PointType = element()
    arrivalPoint: PointType = element()

    class Config:
        xml_root_name = "flight"


class FxaIdType(BaseXmlModel):
    fcaId: Optional[str] = element(default=None)
    fcaName: Optional[str] = element(default=None)
    lastUpdate: Optional[datetime] = element(default=None, parser=isoparse)

    class Config:
        xml_root_name = "fxaId"


class FxaFlightType(BaseXmlModel):
    fxaId: FxaIdType = element()
    bentryTm: Optional[datetime] = element(default=None, parser=isoparse)
    createTm: Optional[datetime] = element(default=None, parser=isoparse)
    eentryTm: Optional[datetime] = element(default=None, parser=isoparse)
    entryTm: Optional[datetime] = element(default=None, parser=isoparse)
    exitTm: Optional[datetime] = element(default=None, parser=isoparse)
    extendedExitTm: Optional[datetime] = element(default=None, parser=isoparse)
    ientryTm: Optional[datetime] = element(default=None, parser=isoparse)
    oentryTm: Optional[datetime] = element(default=None, parser=isoparse)
    entryLat: Optional[float] = element(default=None)
    entryLon: Optional[float] = element(default=None)
    entryHeading: Optional[int] = element(default=None)
    exitInd: Optional[str] = element(default=None)

    class Config:
        xml_root_name = "fxaFlight"


class FxaFlightDataType(BaseXmlModel):
    fxaFlight: List[FxaFlightType] = element()

    class Config:
        xml_root_name = "fxaFlightData"


class TmiType(BaseXmlModel):
    fcaId: Optional[str] = element(default=None)
    updateType: Optional[str] = element(default=None, attrs={"updateType": str})
    lastUpdateTime: Optional[datetime] = element(
        default=None, attrs={"lastUpdateTime": isoparse}
    )

    class Config:
        xml_root_name = "tmi"


class TmiFlightInfoListType(BaseXmlModel):
    tmi: TmiType = element()
    fxaFlightData: FxaFlightDataType = element()

    class Config:
        xml_root_name = "tmiFlightInfoList"


class FlightDataType(BaseXmlModel):
    flight: FlightType = element()
    flightReference: Optional[str] = element(default=None)
    status: Optional[str] = element(default=None)
    tmiFlightInfoList: TmiFlightInfoListType = element()

    class Config:
        xml_root_name = "flightData"


class TmiFlightDataListType(BaseXmlModel):
    flightData: List[FlightDataType] = element()

    class Config:
        xml_root_name = "tmiFlightDataList"


class TmiFlightListModel(BaseXmlModel):
    sensitivity: Optional[str] = element(default=None, attrs={"sensitivity": str})
    visDomain: Optional[str] = element(default=None, attrs={"visDomain": str})
    destinationCodes: Optional[str] = element(
        default=None, attrs={"destinationCodes": str}
    )
    sourceFacility: Optional[str] = element(name="sourceFacility", default=None)
    sourceTimeStamp: Optional[datetime] = element(
        name="sourceTimeStamp", default=None, parser=isoparse
    )
    msgType: Optional[str] = element(default=None, attrs={"msgType": str})
    tmiFlightDataList: TmiFlightDataListType = element(name="tmiFlightDataList")

    class Config:
        xml_root_name = "fiMessage"
