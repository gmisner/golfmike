from typing import Optional, List, Union
from pydantic import BaseModel, Field, ValidationError
import xmltodict
from utils.logger import main_logger as logger
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime

# Logger is already imported as 'logger'

# URL configuration with the correct endpoint ID
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="gkmisner",
    password="81QgOfuHCwyk",
    host="ep-tight-lake-32732521.us-west-2.aws.neon.tech",
    port=5432,
    database="swim",
    query={
        "sslmode": "require",
        "options": "endpoint=ep-tight-lake-32732521",
    },
)

engine = create_engine(connection_string)
Base = declarative_base()


class AircraftDBModel(Base):
    """Class representing aircraft information in the database"""

    __tablename__ = "aircraft"
    aircraft_id = Column(String, primary_key=True)
    gufi = Column(String)
    flight_reference = Column(String)
    status = Column(String)


class FlightPlanDBModel(Base):
    """Class representing flight plan information in the database"""

    __tablename__ = "flight_plan"
    aircraft_id = Column(String, primary_key=True)
    departure_airport = Column(String)
    arrival_airport = Column(String)
    igtd = Column(DateTime)


class TmiUpdatesDBModel(Base):
    """Class representing TMI updates in the database"""

    __tablename__ = "tmi_updates"
    aircraft_id = Column(String, primary_key=True)
    update_time = Column(DateTime, primary_key=True)
    update_type = Column(String)
    last_update_time = Column(DateTime)
    fca_id = Column(String)


class FxaUpdatesDBModel(Base):
    """Class representing FXA updates in the database"""

    __tablename__ = "fxa_updates"
    aircraft_id = Column(String, primary_key=True)
    update_time = Column(DateTime, primary_key=True)
    fxa_id = Column(String)
    entry_time = Column(DateTime)
    create_time = Column(DateTime)
    exit_time = Column(DateTime)
    entry_lat = Column(Float)
    entry_lon = Column(Float)
    entry_heading = Column(Integer)
    exit_ind = Column(String)


class OceanicReportDBModel(Base):
    """Class representing SQLAchemy Oceanic Reporting Data from the SWIM oceanicReport Message"""

    __tablename__ = "oceanic_report"
    id = Column(String, primary_key=True)  # Using 'aircraftId' as ID
    sensitivity = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraftId = Column(String)
    gufi = Column(String)
    igtd = Column(DateTime)
    departurePoint = Column(JSONB)
    arrivalPoint = Column(JSONB)
    speed = Column(Integer)  # Assuming speed is an integer
    plannedPositionData = Column(JSONB)
    reportedPositionData = Column(JSONB)
    ncsmTrackData = Column(JSONB)


class TrackInformationDBModel(Base):
    """Class representing SQLAchemy Track Information Data from the SWIM trackInformation Message"""

    __tablename__ = "track_information"
    id = Column(String, primary_key=True)  # Assuming 'aircraftId' as ID
    sensitivity = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraftId = Column(String)
    gufi = Column(String)
    igtd = Column(DateTime)
    departurePoint = Column(JSONB)
    arrivalPoint = Column(JSONB)
    speed = Column(Integer)  # Assuming speed is an integer
    reportedAltitude = Column(JSONB)
    position = Column(JSONB)
    timeAtPosition = Column(DateTime)
    ncsmTrackData = Column(JSONB)
    ncsmRouteData = Column(JSONB)


class FlightSectorsDBModel(Base):
    """Class representing SQLAchemy Flight Sectors Data from the SWIM flightSectors Message"""

    __tablename__ = "flight_sectors"
    id = Column(String, primary_key=True)  # Using 'aircraftId' as ID
    sensitivity = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraftId = Column(String)
    gufi = Column(String)
    departurePoint = Column(JSONB)
    arrivalPoint = Column(JSONB)
    sectorDesignator = Column(String)
    sectorEntryTime = Column(DateTime)
    sectorExitTime = Column(DateTime)
    entryPoint = Column(JSONB)
    exitPoint = Column(JSONB)
    crossingAltitude = Column(Float)
    crossingSpeed = Column(Integer)
    flightLevel = Column(String)
    routeOfFlight = Column(String)
    trajectory = Column(JSONB)


class TmiFlightListDBModel(Base):
    """Class representing SQLAchemy Basic Flight Data from the SWIM TMI_FLIGHT_LIST Message"""

    __tablename__ = "tmi_flight_list"
    id = Column(String, primary_key=True)  # Using 'aircraftId' as ID
    sensitivity = Column(String)
    visDomain = Column(String)
    destinationCodes = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraftId = Column(String)
    gufi = Column(String)
    igtd = Column(DateTime)
    flightReference = Column(String)
    status = Column(String)
    tmiFlightInfoList = Column(JSONB)
    fxaFlightData = Column(JSONB)


# Create all tables
Base.metadata.create_all(bind=engine)


class FxaId(BaseModel):
    """Pydantic model representing FXA ID structure"""

    fcaId: str = Field(..., alias="fcaId")
    fcaName: str = Field(..., alias="fcaName")
    lastUpdate: str = Field(..., alias="lastUpdate")  # Type is str


class Tmi(BaseModel):
    """Pydantic model representing TMI structure"""

    updateType: str = Field(..., alias="updateType")
    lastUpdateTime: str = Field(..., alias="lastUpdateTime")  # Type is str
    fcaId: Optional[str]


class FxaFlight(BaseModel):
    """Pydantic model representing FXA Flight structure"""

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
    """Pydantic model representing Flight Sectors structure"""

    id: str  # Using 'aircraftId' as ID
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
    """Pydantic model representing TMI Flight List structure"""

    id: str  # Using 'aircraftId' as ID
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
        json_encoders = {
            datetime: lambda v: (
                v.isoformat() if v else None
            ),  # Handle potential None values
        }


class Airport(BaseModel):
    """Pydantic model representing Airport structure"""

    airport: str


class AssignedAltitude(BaseModel):
    """Pydantic model representing Assigned Altitude structure"""

    simpleAltitude: str


class ReportedAltitude(BaseModel):
    """Pydantic model representing Reported Altitude structure"""

    assignedAltitude: AssignedAltitude


class LatitudeDMS(BaseModel):
    """Pydantic model representing Latitude DMS structure"""

    degrees: int
    direction: str
    minutes: int
    seconds: Optional[int]


class LongitudeDMS(BaseModel):
    """Pydantic model representing Longitude DMS structure"""

    degrees: int
    direction: str
    minutes: int
    seconds: Optional[int]


class Position(BaseModel):
    """Pydantic model representing Position structure"""

    latitude: LatitudeDMS
    longitude: LongitudeDMS


class PlannedPositionData(BaseModel):
    """Pydantic model representing Planned Position Data structure"""

    planNumber: int = Field(..., alias="planNumber")
    position: Position
    altitude: int
    time: Union[datetime, str]


class ReportedPositionData(BaseModel):
    """Pydantic model representing Reported Position Data structure"""

    position: Position
    altitude: int
    time: Union[datetime, str]


class Eta(BaseModel):
    """Pydantic model representing ETA structure"""

    etaType: str = Field(..., alias="etaType")
    timeValue: Union[datetime, str]


class RvsmData(BaseModel):
    """Pydantic model representing RVSM Data structure"""

    currentCompliance: bool = Field(..., alias="currentCompliance")
    equipped: bool
    futureCompliance: bool = Field(..., alias="futureCompliance")


class ArrivalFixAndTime(BaseModel):
    """Pydantic model representing Arrival Fix and Time structure"""

    arrTime: Union[datetime, str]
    fixName: str = Field(..., alias="fixName")


class DepartureFixAndTime(BaseModel):
    """Pydantic model representing Departure Fix and Time structure"""

    arrTime: Union[datetime, str]
    fixName: str = Field(..., alias="fixName")


class NextEvent(BaseModel):
    """Pydantic model representing Next Event structure"""

    latitudeDecimal: float = Field(..., alias="latitudeDecimal")
    longitudeDecimal: float = Field(..., alias="longitudeDecimal")


class NcsmTrackData(BaseModel):
    """Pydantic model representing NCSM Track Data structure"""

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
    """Pydantic model representing Track Information structure"""

    id: str  # Using 'aircraftId' as ID
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
    ncsmRouteData: Optional[dict] = Field(
        None, alias="ncsmRouteData"
    )  # Assuming this is a complex dictionary

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class OceanicReportModel(BaseModel):
    """Pydantic model representing Oceanic Report structure"""

    id: str  # Using 'aircraftId' as ID
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


def parse_xml_to_pydantic(xml_data):
    """
    Parses XML data into Pydantic models.

    Args:
        xml_data (str): XML data to be parsed.

    Returns:
        Union[None, TmiFlightListModel, FlightSectorsModel, TrackInformationModel, OceanicReportModel]: Parsed Pydantic model or None.
    """
    try:
        xml_dict = xmltodict.parse(
            xml_data,
            process_namespaces=True,
            namespaces={
                "urn:us:gov:dot:faa:atm:tfm:tfmdataservice": None,
                "urn:us:gov:dot:faa:atm:tfm:flowinformation": None,
                "urn:us:gov:dot:faa:atm:tfm:ficommonmessages2": None,
                "urn:us:gov:dot:faa:atm:tfm:flightdata": None,
                "urn:us:gov:dot:faa:atm:tfm:tfmdatacoreelements": None,
                "urn:us:gov:dot:faa:atm:tfm:flightdatacommonmessages": None,
            },
        )

        if "tfmDataService" in xml_dict:
            tfm_data = xml_dict["tfmDataService"]  # Access the 'tfmDataService' element

            if "fltdOutput" in tfm_data:  # Check inside 'tfmDataService'
                # Handle 'trackInformation' and 'oceanicReport' messages
                # (No changes needed in this section)
                pass  # You need to add your logic here for 'fltdOutput'

            if "fiOutput" in tfm_data:  # Check inside 'tfmDataService'
                # Handle 'TMI_FLIGHT_LIST' and 'FlightSectors' messages
                fi_message = tfm_data["fiOutput"]["fiMessage"]
                msg_type = fi_message.get("@msgType")
                sensitivity = fi_message.get("@sensitivity")
                vis_domain = fi_message.get("@visDomain")
                destination_codes = fi_message.get("@destinationCodes")
                source_facility = fi_message.get("@sourceFacility")
                source_time_stamp = fi_message.get("@sourceTimeStamp")
                if source_time_stamp:
                    try:
                        source_time_stamp = datetime.fromisoformat(source_time_stamp)
                    except ValueError:
                        source_time_stamp = None

                if msg_type == "TMI_FLIGHT_LIST":
                    flight_data_list = fi_message.get("tmiFlightDataList", {}).get(
                        "flightData", []
                    )
                    if not isinstance(flight_data_list, list):
                        flight_data_list = [flight_data_list]

                    for flight_data in flight_data_list:
                        if isinstance(flight_data, dict):
                            aircraft_id = flight_data.get("flight", {}).get(
                                "aircraftId"
                            )
                            gufi = flight_data.get("flight", {}).get("gufi")
                            igtd = flight_data.get("flight", {}).get("igtd")
                            if igtd:
                                try:
                                    igtd = datetime.fromisoformat(igtd)
                                except ValueError:
                                    igtd = None
                            departure_point_data = flight_data.get("flight", {}).get(
                                "departurePoint", {}
                            )
                            departure_point = (
                                Airport(**departure_point_data)
                                if departure_point_data
                                else None
                            )

                            arrival_point_data = flight_data.get("flight", {}).get(
                                "arrivalPoint", {}
                            )
                            arrival_point = (
                                Airport(**arrival_point_data)
                                if arrival_point_data
                                else None
                            )

                            tmi_flight_info_list = flight_data.get(
                                "tmiFlightInfoList", {}
                            ).get("tmi", [])
                            if not isinstance(tmi_flight_info_list, list):
                                tmi_flight_info_list = [tmi_flight_info_list]

                            fxa_flight_data_list = flight_data.get(
                                "fxaFlightData", {}
                            ).get("fxaFlight", [])
                            if not isinstance(fxa_flight_data_list, list):
                                fxa_flight_data_list = [fxa_flight_data_list]

                            flight_reference = flight_data.get("flightReference")
                            status = flight_data.get("status")

                            tmi_data_list = []
                            for tmi_item in tmi_flight_info_list:
                                if isinstance(tmi_item, dict):
                                    tmi_update_type = tmi_item.get(
                                        "@updateType", "UNKNOWN"
                                    )
                                    tmi_last_update_time = tmi_item.get(
                                        "@lastUpdateTime"
                                    )
                                    tmi_fca_id = tmi_item.get("fcaId")

                                    if tmi_last_update_time:
                                        try:
                                            tmi_last_update_time = (
                                                datetime.fromisoformat(
                                                    tmi_last_update_time
                                                ).isoformat()
                                            )
                                        except ValueError:
                                            tmi_last_update_time = (
                                                datetime.now().isoformat()
                                            )

                                    tmi_data = Tmi(
                                        updateType=tmi_update_type,
                                        lastUpdateTime=tmi_last_update_time,
                                        fcaId=tmi_fca_id,
                                    )
                                    tmi_data_list.append(tmi_data)

                            fxa_flight_data = []
                            for fxa_flight_item in fxa_flight_data_list:
                                if isinstance(fxa_flight_item, dict):
                                    fxa_id_data = fxa_flight_item.get("fxaId", {})
                                    fxa_id = FxaId(
                                        fcaId=fxa_id_data.get("fcaId", "UNKNOWN"),
                                        fcaName=fxa_id_data.get("fcaName", "UNKNOWN"),
                                        lastUpdate=fxa_id_data.get(
                                            "lastUpdate", datetime.now().isoformat()
                                        ),
                                    )

                                    fxa_flight = FxaFlight(
                                        fxaId=fxa_id,
                                        bentryTm=fxa_flight_item.get("bentryTm"),
                                        createTm=fxa_flight_item.get("createTm"),
                                        eentryTm=fxa_flight_item.get("eentryTm"),
                                        entryTm=fxa_flight_item.get("entryTm"),
                                        exitTm=fxa_flight_item.get("exitTm"),
                                        extendedExitTm=fxa_flight_item.get(
                                            "extendedExitTm"
                                        ),
                                        ientryTm=fxa_flight_item.get("ientryTm"),
                                        oentryTm=fxa_flight_item.get("oentryTm"),
                                        entryLat=fxa_flight_item.get("entryLat"),
                                        entryLon=fxa_flight_item.get("entryLon"),
                                        entryHeading=fxa_flight_item.get(
                                            "entryHeading"
                                        ),
                                        exitInd=fxa_flight_item.get("exitInd"),
                                    )
                                    fxa_flight_data.append(fxa_flight)

                            return TmiFlightListModel(
                                id=aircraft_id,
                                sensitivity=sensitivity,
                                visDomain=vis_domain,
                                destinationCodes=destination_codes,
                                sourceFacility=source_facility,
                                sourceTimeStamp=source_time_stamp,
                                msgType=msg_type,
                                aircraftId=aircraft_id,
                                gufi=gufi,
                                igtd=igtd,
                                departurePoint=departure_point,
                                arrivalPoint=arrival_point,
                                flightReference=flight_reference,
                                status=status,
                                tmiFlightInfoList=tmi_data_list,
                                fxaFlightData=fxa_flight_data,
                            )
                        else:
                            logger.warning(
                                "Unexpected data format for 'flight_data'. It's not a dictionary. Skipping this entry."
                            )
                            # You might want to log the flight_data here for debugging

                elif msg_type == "FlightSectors":
                    # ... (Your existing logic for 'FlightSectors') ...
                    pass  # Add your logic here for 'FlightSectors'

                else:
                    logger.warning(
                        f"Unknown message type: {msg_type}. Skipping message."
                    )

            else:
                logger.warning(
                    f"Unknown element found in 'tfmDataService'. Skipping Message"
                )
                return None
        else:
            logger.warning(f"Unknown XML structure. No 'tfmDataService' element found.")
        return None

    except Exception as e:
        logger.error(f"Error parsing XML to Pydantic: {e}", exc_info=True)
        return None


def parse_and_store_to_database(xml_data):
    parsed_data = parse_xml_to_pydantic(xml_data)
    if parsed_data is not None:
        try:
            flight_data_dict = parsed_data.dict()

            if isinstance(parsed_data, TmiFlightListModel):
                tmi_data_list = flight_data_dict.pop("tmiFlightInfoList", [])
                fxa_flight_data = flight_data_dict.pop("fxaFlightData", [])

                with Session() as session:
                    # Store or update aircraft data
                    aircraft_data = {
                        "aircraft_id": flight_data_dict["aircraftId"],
                        "gufi": flight_data_dict["gufi"],
                        "flight_reference": flight_data_dict["flightReference"],
                        "status": flight_data_dict["status"],
                    }
                    stmt = insert(AircraftDBModel.__table__).values(**aircraft_data)
                    update_dict = {c.name: c for c in stmt.excluded}
                    update_stmt = stmt.on_conflict_do_update(
                        index_elements=["aircraft_id"], set_=update_dict
                    )
                    session.execute(update_stmt)

                    # Store flight plan
                    departure_point = flight_data_dict.get("departurePoint")
                    arrival_point = flight_data_dict.get("arrivalPoint")
                    departure_airport = (
                        departure_point.get("airport") if departure_point else None
                    )
                    arrival_airport = (
                        arrival_point.get("airport") if arrival_point else None
                    )
                    flight_plan_data = {
                        "aircraft_id": flight_data_dict["aircraftId"],
                        "departure_airport": departure_airport,
                        "arrival_airport": arrival_airport,
                        "igtd": flight_data_dict.get("igtd"),
                    }
                    stmt = insert(FlightPlanDBModel.__table__).values(
                        **flight_plan_data
                    )
                    update_dict = {c.name: c for c in stmt.excluded}
                    update_stmt = stmt.on_conflict_do_update(
                        index_elements=["aircraft_id"], set_=update_dict
                    )
                    session.execute(update_stmt)

                    # Store TMI updates
                    for tmi in tmi_data_list:
                        update_time = (
                            flight_data_dict.get("sourceTimeStamp")
                            or datetime.now().isoformat()
                        )
                        tmi_data = {
                            "aircraft_id": flight_data_dict["aircraftId"],
                            "update_time": update_time,
                            "update_type": tmi["updateType"],
                            "last_update_time": tmi["lastUpdateTime"],
                            "fca_id": tmi["fcaId"],
                        }
                        stmt = insert(TmiUpdatesDBModel.__table__).values(**tmi_data)
                        update_dict = {c.name: c for c in stmt.excluded}
                        update_stmt = stmt.on_conflict_do_update(
                            index_elements=["aircraft_id", "update_time"],
                            set_=update_dict,
                        )
                        session.execute(update_stmt)

                    # Store FXA updates
                    for fxa in fxa_flight_data:
                        update_time = (
                            flight_data_dict.get("sourceTimeStamp")
                            or datetime.now().isoformat()
                        )
                        fxa_data = {
                            "aircraft_id": flight_data_dict["aircraftId"],
                            "update_time": update_time,
                            "fxa_id": fxa["fxaId"],
                            "entry_time": fxa["entryTm"],
                            "create_time": fxa["createTm"],
                            "exit_time": fxa["exitTm"],
                            "entry_lat": fxa["entryLat"],
                            "entry_lon": fxa["entryLon"],
                            "entry_heading": fxa["entryHeading"],
                            "exit_ind": fxa["exitInd"],
                        }
                        stmt = insert(FxaUpdatesDBModel.__table__).values(**fxa_data)
                        update_dict = {c.name: c for c in stmt.excluded}
                        update_stmt = stmt.on_conflict_do_update(
                            index_elements=["aircraft_id", "update_time"],
                            set_=update_dict,
                        )
                        session.execute(update_stmt)

                    session.commit()

            logger.info(f"Successfully stored data.")
        except IntegrityError as e:
            logger.error(f"Integrity error storing to database: {e}", exc_info=True)
            session.rollback()
        except Exception as e:
            logger.error(f"Error storing to database: {e}", exc_info=True)
            session.rollback()
    else:
        logger.error("Failed to parse XML data.")


Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
