from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Integer,
    Float,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.engine.url import URL

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


class WaypointDBModel(Base):
    """Class representing aircraft waypoints in the database"""

    __tablename__ = "waypoints"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), index=True)
    waypoint_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    timestamp = Column(DateTime)

    aircraft = relationship("AircraftDBModel", back_populates="waypoints")


class AircraftDBModel(Base):
    """Class representing aircraft information in the database"""

    __tablename__ = "aircraft"
    aircraft_id = Column(String, primary_key=True)
    gufi = Column(String)
    flight_reference = Column(String)
    status = Column(String)

    flight_plans = relationship("FlightPlanDBModel", back_populates="aircraft")
    tmi_updates = relationship("TmiUpdatesDBModel", back_populates="aircraft")
    fxa_updates = relationship("FxaUpdatesDBModel", back_populates="aircraft")
    oceanic_reports = relationship("OceanicReportDBModel", back_populates="aircraft")
    track_informations = relationship(
        "TrackInformationDBModel", back_populates="aircraft"
    )
    flight_sectors = relationship("FlightSectorsDBModel", back_populates="aircraft")
    tmi_flight_lists = relationship("TmiFlightListDBModel", back_populates="aircraft")


class FlightPlanDBModel(Base):
    """Class representing flight plan information in the database"""

    __tablename__ = "flight_plan"
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), primary_key=True)
    departure_airport = Column(String)
    arrival_airport = Column(String)
    igtd = Column(DateTime)

    aircraft = relationship("AircraftDBModel", back_populates="flight_plans")


class TmiUpdatesDBModel(Base):
    """Class representing TMI updates in the database"""

    __tablename__ = "tmi_updates"
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), primary_key=True)
    update_time = Column(DateTime, primary_key=True)
    update_type = Column(String)
    last_update_time = Column(DateTime)
    fca_id = Column(String)

    aircraft = relationship("AircraftDBModel", back_populates="tmi_updates")


class FxaUpdatesDBModel(Base):
    """Class representing FXA updates in the database"""

    __tablename__ = "fxa_updates"
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), primary_key=True)
    update_time = Column(DateTime, primary_key=True)
    fxa_id = Column(String)
    entry_time = Column(DateTime)
    create_time = Column(DateTime)
    exit_time = Column(DateTime)
    entry_lat = Column(Float)
    entry_lon = Column(Float)
    entry_heading = Column(Integer)
    exit_ind = Column(String)

    aircraft = relationship("AircraftDBModel", back_populates="fxa_updates")


class OceanicReportDBModel(Base):
    """Class representing SQLAchemy Oceanic Reporting Data from the SWIM oceanicReport Message"""

    __tablename__ = "oceanic_report"
    id = Column(String, primary_key=True)  # Using 'aircraftId' as ID
    sensitivity = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    gufi = Column(String)
    igtd = Column(DateTime)
    departurePoint = Column(JSONB)
    arrivalPoint = Column(JSONB)
    speed = Column(Integer)  # Assuming speed is an integer
    plannedPositionData = Column(JSONB)
    reportedPositionData = Column(JSONB)
    ncsmTrackData = Column(JSONB)

    aircraft = relationship("AircraftDBModel", back_populates="oceanic_reports")


class TrackInformationDBModel(Base):
    """Class representing SQLAchemy Track Information Data from the SWIM trackInformation Message"""

    __tablename__ = "track_information"
    id = Column(String, primary_key=True)  # Assuming 'aircraftId' as ID
    sensitivity = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
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

    aircraft = relationship("AircraftDBModel", back_populates="track_informations")


class FlightSectorsDBModel(Base):
    """Class representing SQLAchemy Flight Sectors Data from the SWIM flightSectors Message"""

    __tablename__ = "flight_sectors"
    id = Column(String, primary_key=True)
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
    trajectory = Column(JSONB)  # Store the list of sectors as JSON

    aircraft = relationship("AircraftDBModel", back_populates="flight_sectors")


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
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    gufi = Column(String)
    igtd = Column(DateTime)
    flightReference = Column(String)
    status = Column(String)
    tmiFlightInfoList = Column(JSONB)
    fxaFlightData = Column(JSONB)

    aircraft = relationship("AircraftDBModel", back_populates="tmi_flight_lists")


# Create all tables
Base.metadata.create_all(bind=engine)

# Database session factory
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
