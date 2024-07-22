from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from models.base import Base


class FxaUpdatesDBModel(Base):
    __tablename__ = "fxa_updates"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    flight_plan_id = Column(String, ForeignKey("flight_plan.flight_plan_id"))
    fca_id = Column(String)
    fca_name = Column(String)
    update_time = Column(DateTime)
    last_update = Column(DateTime)
    bentry_tm = Column(DateTime)
    create_tm = Column(DateTime)
    eentry_tm = Column(DateTime)
    entry_tm = Column(DateTime)
    exit_tm = Column(DateTime)
    extended_exit_tm = Column(DateTime)
    ientry_tm = Column(DateTime)
    oentry_tm = Column(DateTime)
    entry_lat = Column(Float)
    entry_lon = Column(Float)
    entry_heading = Column(Integer)
    exit_ind = Column(String)
    flight_plan = relationship("FlightPlanDBModel", back_populates="fxa_updates")
    aircraft = relationship("AircraftDBModel", back_populates="fxa_updates")
