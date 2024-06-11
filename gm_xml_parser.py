from pydantic import BaseModel, Field, ValidationError
import xmltodict
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import URL
from datetime import datetime

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
        "options": "endpoint=ep-tight-lake-32732521"  # Make sure the endpoint ID is correct
    }
)

engine = create_engine(connection_string)
Base = declarative_base()

class FlightDataDBModel(Base):
    __tablename__ = "flight_data"
    id = Column(String, primary_key=True)
    sensitivity = Column(String)
    visDomain = Column(String)
    destinationCodes = Column(String)
    sourceFacility = Column(String)
    sourceTimeStamp = Column(DateTime)
    msgType = Column(String)
    aircraftId = Column(String)
    gufi = Column(String)
    igtd = Column(DateTime)
    departurePoint = Column(String)
    arrivalPoint = Column(String)
    flightReference = Column(String)
    status = Column(String)
    tmiUpdateType = Column(String)
    tmiLastUpdateTime = Column(DateTime)
    fcaId = Column(String)
    fxaId = Column(String)
    bentryTm = Column(DateTime)
    createTm = Column(DateTime)
    eentryTm = Column(DateTime)
    entryTm = Column(DateTime)
    exitTm = Column(DateTime)
    extendedExitTm = Column(DateTime)
    ientryTm = Column(DateTime)
    oentryTm = Column(DateTime)
    entryLat = Column(String)
    entryLon = Column(String)
    entryHeading = Column(String)
    exitInd = Column(String)

class FlightDataModel(BaseModel):
    sensitivity: str
    visDomain: str
    destinationCodes: str
    sourceFacility: str
    sourceTimeStamp: datetime = Field(..., alias='sourceTimeStamp')
    msgType: str
    aircraftId: str
    gufi: str
    igtd: datetime = Field(..., alias='igtd')
    departurePoint: str
    arrivalPoint: str
    flightReference: str
    status: str
    tmiUpdateType: str
    tmiLastUpdateTime: datetime = Field(..., alias='tmiLastUpdateTime')
    fcaId: str
    fxaId: str
    bentryTm: datetime = Field(..., alias='bentryTm')
    createTm: datetime = Field(..., alias='createTm')
    eentryTm: datetime = Field(..., alias='eentryTm')
    entryTm: datetime = Field(..., alias='entryTm')
    exitTm: datetime = Field(..., alias='exitTm')
    extendedExitTm: datetime = Field(..., alias='extendedExitTm')
    ientryTm: datetime = Field(..., alias='ientryTm')
    oentryTm: datetime = Field(..., alias='oentryTm')
    entryLat: str
    entryLon: str
    entryHeading: str
    exitInd: str

def parse_xml_to_pydantic(xml_data):
    try:
        xml_dict = xmltodict.parse(xml_data)
        flight_data = xml_dict.get("tfmDataService", {}).get("fiOutput", {}).get("fiMessage", {}).get("tmiFlightDataList", {}).get("flightData", {})
        return FlightDataModel(**flight_data)
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None

def parse_and_store_to_database(xml_data):
    parsed_data = parse_xml_to_pydantic(xml_data)
    if parsed_data:
        flight_data_db_model = FlightDataDBModel(**parsed_data.dict())
        with Session() as session:
            session.add(flight_data_db_model)
            session.commit()
        return parsed_data
    else:
        print("Failed to parse XML data")

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
