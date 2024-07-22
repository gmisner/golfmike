from typing import Optional, List
from pydantic_xml import BaseXmlModel, element
from pydantic import RootModel, BaseModel
from datetime import datetime
from dateutil.parser import isoparse


class FlightSectorsModel(BaseXmlModel):
    acid: str = element(default="")
    airline: Optional[str] = element(default=None)
    arrArpt: Optional[str] = element(default=None)
    cdmPart: Optional[bool] = element(default=None)
    depArpt: Optional[str] = element(default=None)
    fdTrigger: Optional[str] = element(default=None)
    flightRef: Optional[str] = element(default=None)
    major: Optional[str] = element(default=None)
    msgType: Optional[str] = element(default=None)
    sensitivity: Optional[str] = element(default=None)
    sourceFacility: Optional[str] = element(default=None)
    sourceTimeStamp: Optional[datetime] = element(default=None, parser=isoparse)
    ncsmFlightSectors: "NcsmFlightSectorsType" = element()

    class Config:
        xml_root_name = "fltdMessage"


class NcsmFlightSectorsType(BaseXmlModel):
    qualifiedAircraftId: "QualifiedAircraftIdType" = element()
    flightTraversalData2: "FlightTraversalData2Type" = element()

    class Config:
        xml_root_name = "ncsmFlightSectors"


class QualifiedAircraftIdType(BaseXmlModel):
    aircraftId: str = element(default=None)
    computerId: "ComputerIdType" = element()
    gufi: Optional[str] = element(default=None)
    igtd: Optional[datetime] = element(default=None, parser=isoparse)
    departurePoint: "PointType" = element()
    arrivalPoint: "PointType" = element()
    aircraftCategory: Optional[str] = element(
        default=None, attrs={"aircraftCategory": str}
    )
    userCategory: Optional[str] = element(default=None, attrs={"userCategory": str})

    class Config:
        xml_root_name = "qualifiedAircraftId"


class FlightTraversalData2Type(BaseXmlModel):
    fix: List["FixType"] = element()
    waypoint: List["WaypointType"] = element()
    airway: List["AirwayType"] = element()
    center: List["CenterType"] = element()
    sector: List["SectorType"] = element()

    class Config:
        xml_root_name = "flightTraversalData2"


# BaseModel for Fix data
class FixData(BaseModel):
    sequenceNumber: Optional[int]
    elapsedTime: Optional[int]


# RootModel for FixType
class FixType(RootModel):
    root: FixData = element(
        default=FixData(sequenceNumber=None, elapsedTime=None), root_element=True
    )


class WaypointType(BaseXmlModel):
    # Define fields as regular elements
    waypoint_text: Optional[str] = element(
        default=None
    )  # Replace with your actual field name
    latitudeDecimal: Optional[float] = element(
        default=None, attrs={"latitudeDecimal": float}
    )
    longitudeDecimal: Optional[float] = element(
        default=None, attrs={"longitudeDecimal": float}
    )
    sequenceNumber: Optional[int] = element(default=None, attrs={"sequenceNumber": int})
    elapsedTime: Optional[int] = element(default=None, attrs={"elapsedTime": int})

    class Config:
        xml_root_name = "waypoint"


# BaseModel for Airway data
class AirwayData(BaseModel):
    sequenceNumber: Optional[int]


# RootModel for AirwayType
class AirwayType(RootModel):
    root: AirwayData = element(
        default=AirwayData(sequenceNumber=None), root_element=True
    )


# BaseModel for Center data
class CenterData(BaseModel):
    sequenceNumber: Optional[int]
    elapsedEntryTime: Optional[int]


# RootModel for CenterType
class CenterType(RootModel):
    root: CenterData = element(
        default=CenterData(sequenceNumber=None, elapsedEntryTime=None),
        root_element=True,
    )


# BaseModel for Sector data
class SectorData(BaseModel):
    sequenceNumber: Optional[int]
    elapsedEntryTime: Optional[int]


# RootModel for SectorType
class SectorType(RootModel):
    root: SectorData = element(
        default=SectorData(sequenceNumber=None, elapsedEntryTime=None),
        root_element=True,
    )


class PointType(BaseXmlModel):
    airport: Optional[str] = element(default=None)

    class Config:
        xml_root_name = "departurePoint"  # Assuming same structure for arrivalPoint


class ComputerIdType(BaseXmlModel):
    facilityIdentifier: Optional[str] = element(default=None)

    class Config:
        xml_root_name = "computerId"
