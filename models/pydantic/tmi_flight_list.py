from typing import List, Optional
from pydantic import BaseModel


class FxaFlight(BaseModel):
    """
    FxaFlight _summary_

    Args:
        BaseModel (_type_): _description_
    """

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
    """
    FxaFlightData _summary_

    Args:
        BaseModel (_type_): _description_
    """

    fxaFlight: List[FxaFlight]


class Tmi(BaseModel):
    """
    Tmi _summary_

    Args:
        BaseModel (_type_): _description_
    """

    updateType: Optional[str]
    lastUpdateTime: Optional[str]
    fcaId: Optional[str]


class TmiFlightInfoList(BaseModel):
    """
    TmiFlightInfoList _summary_

    Args:
        BaseModel (_type_): _description_
    """

    tmi: Optional[Tmi]
    fxaFlightData: Optional[FxaFlightData]


class FlightDataType(BaseModel):
    """
    FlightDataType _summary_

    Args:
        BaseModel (_type_): _description_
    """

    aircraftId: Optional[str]
    gufi: Optional[str]
    igtd: Optional[str]
    departurePoint: Optional[str]
    arrivalPoint: Optional[str]
    flightReference: Optional[str]
    status: Optional[str]


class TmiFlightListModel(BaseModel):
    """
    TmiFlightListModel _summary_

    Args:
        BaseModel (_type_): _description_
    """

    flight: FlightDataType
    tmiFlightInfoList: TmiFlightInfoList

    class Config:
        """
        _summary_
        """

        from_attributes = True
