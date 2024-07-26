# models/sqlalchemy/track_information.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from models.base import Base
from sqlalchemy.orm import relationship


class TrackInformationDBModel(Base):
    __tablename__ = "track_information"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    gufi = Column(String)
    speed = Column(Integer)
    altitude = Column(Integer)
    latitude = Column(String)
    longitude = Column(String)
    time_at_position = Column(String)
    departure_airport = Column(String)
    arrival_airport = Column(String)
    aircraft = relationship("AircraftDBModel", back_populates="track_information")
