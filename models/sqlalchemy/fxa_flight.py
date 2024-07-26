# models/sqlalchemy/fxa_flight.py
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from models.base import Base


class FxaFlightDBModel(Base):
    __tablename__ = "fxa_flight"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))
    flight_plan_id = Column(Integer, ForeignKey("flight_plan.id"))
    fxa_id = Column(String)
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

    flight_plan = relationship("FlightPlanDBModel", back_populates="fxa_flight")
    aircraft = relationship("AircraftDBModel", back_populates="fxa_flight")
