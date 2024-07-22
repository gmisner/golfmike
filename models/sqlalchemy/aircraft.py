# models/sqlalchemy/aircraft.py

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from db_config import Base


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
    track_data = relationship("TrackDBModel", back_populates="aircraft")
    status_updates = relationship("StatusDBModel", back_populates="aircraft")
