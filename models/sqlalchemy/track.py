from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class TrackDBModel(Base):
    __tablename__ = "tracks"
    id = Column(String, primary_key=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    sourceId_00e = Column(String)
    sourceTime_00e1 = Column(String)
    sourceSeqNo_00e2 = Column(String)
    flightId_02a = Column(String)
    computerId_02d = Column(String)
    sspId_167a = Column(String)
    groundSpeed_05b = Column(String)
    assignedAlt_08a = Column(String)
    reportedAlt_54a = Column(String)
    reportedAlt_54b = Column(String)
    reportedAlt_54c = Column(String)
    controllingFacility_138a = Column(String)
    controllingSector_138b = Column(String)
    receivingFacility_139a = Column(String)
    receivingSector_139b = Column(String)
    trackPosition_23d = Column(String)
    trackVelocity_23e = Column(String)
    coastIndicator_153a = Column(String)
    timeOfTrackData_170a = Column(DateTime)
    targetPosition_171a = Column(String)
    targetAlt_172a = Column(String)
    targetAltInvalid_172b = Column(String)
    timeOfTargetData_173a = Column(DateTime)
    # Define the relationship with AircraftDBModel
    aircraft = relationship("AircraftDBModel", back_populates="track_data")
