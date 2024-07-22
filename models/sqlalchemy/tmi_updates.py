# models/sqlalchemy/tmi_updates.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from .aircraft import AircraftDBModel

Base = declarative_base()


class TmiUpdatesDBModel(Base):
    """Class representing TMI updates in the database"""

    __tablename__ = "tmi_updates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    update_time = Column(DateTime)
    update_type = Column(String)
    last_update_time = Column(DateTime)
    fca_id = Column(String)
    aircraft = relationship("AircraftDBModel", back_populates="tmi_updates")
