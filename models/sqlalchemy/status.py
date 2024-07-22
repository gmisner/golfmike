from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from db_config import Base


class StatusDBModel(Base):
    __tablename__ = "status_updates"
    id = Column(String, primary_key=True)
    classification = Column(String)
    time = Column(DateTime)
    statusType = Column(String)
    source = Column(String)
    artcc = Column(JSONB)  # Store the artcc list as JSON
    software = Column(String)
    process = Column(String)
    details = Column(String)
    numberOfMsgs = Column(Integer)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    aircraft = relationship("AircraftDBModel", back_populates="status_updates")
