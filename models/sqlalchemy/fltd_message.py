from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class FltdMessageDBModel(Base):
    __tablename__ = "fltd_message"

    id = Column(String, primary_key=True)
    sourceTimeStamp = Column(DateTime)
    trackInformation_id = Column(String, ForeignKey("track_information.id"))
    cdmPart = Column(Boolean)

    trackInformation = relationship(
        "TrackInformationDBModel", back_populates="fltdMessages"
    )


class TrackInformationDBModel(Base):
    __tablename__ = "track_information"

    id = Column(String, primary_key=True)
    aircraftId = Column(String)
    computerId = Column(String)
    facilityIdentifier = Column(String)
    idNumber = Column(String)
    gufi = Column(String)
    igtd = Column(DateTime)
    departurePoint = Column(String)
    arrivalPoint = Column(String)
    speed = Column(Integer)
    assignedAltitude = Column(String)
    latitude = Column(String)
    longitude = Column(String)
    timeAtPosition = Column(DateTime)
    eta = Column(DateTime, nullable=True)
    rvsmCompliance = Column(Boolean)

    fltdMessages = relationship("FltdMessageDBModel", back_populates="trackInformation")
