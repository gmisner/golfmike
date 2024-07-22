from sqlalchemy import Column, String, Integer
from models.base import Base
from sqlalchemy.orm import relationship


class AircraftDBModel(Base):
    __tablename__ = "aircraft"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, unique=True, index=True)
    flight_plan = relationship("FlightPlanDBModel", back_populates="aircraft")
    tmi_updates = relationship("TmiUpdatesDBModel", back_populates="aircraft")
    fxa_updates = relationship("FxaUpdatesDBModel", back_populates="aircraft")
    track_data = relationship("TrackDBModel", back_populates="aircraft")
    status_updates = relationship("StatusDBModel", back_populates="aircraft")
