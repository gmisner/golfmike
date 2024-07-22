from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from models.base import Base
from sqlalchemy.orm import relationship


class TmiUpdatesDBModel(Base):
    __tablename__ = "tmi_updates"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    update_time = Column(DateTime)
    update_type = Column(String)
    last_update_time = Column(DateTime)
    fca_id = Column(String)

    aircraft = relationship("AircraftDBModel", back_populates="tmi_updates")
