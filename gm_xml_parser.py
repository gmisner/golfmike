# xml_parser.py

from pydantic import BaseModel
import xmltodict
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import URL


# URL configuration
connection_string = URL(
    "postgresql",
    username="gkmisner",
    password="81QgOfuHCwyk",
    host="ep-tight-lake-32732521.us-west-2.aws.neon.tech",
    port=5432,  # Change the port number if it's different
    database="swim",
    query={"sslmode": "require", "options": "endpoint%3Dep-tight-lake-32732521"},
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
    sourceTimeStamp: str
    msgType: str
    aircraftId: str
    gufi: str
    igtd: str
    departurePoint: str
    arrivalPoint: str
    flightReference: str
    status: str
    tmiUpdateType: str
    tmiLastUpdateTime: str
    fcaId: str
    fxaId: str
    bentryTm: str
    createTm: str
    eentryTm: str
    entryTm: str
    exitTm: str
    extendedExitTm: str
    ientryTm: str
    oentryTm: str
    entryLat: str
    entryLon: str
    entryHeading: str
    exitInd: str


def parse_xml_to_pydantic(xml_data):
    xml_dict = xmltodict.parse(xml_data)
    return FlightDataModel(
        **xml_dict.get("tfmDataService", {})
        .get("fiOutput", {})
        .get("fiMessage", {})
        .get("tmiFlightDataList", {})
        .get("flightData", {})
    )


def parse_and_store_to_database(xml_data):
    parsed_data = parse_xml_to_pydantic(xml_data)

    flight_data_model = FlightDataDBModel(**parsed_data.dict())
    session = Session()
    session.add(flight_data_model)
    session.commit()

    return parsed_data


Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
