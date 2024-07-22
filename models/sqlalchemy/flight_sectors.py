from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from models import Base

class FlightSectorsDBModel(Base):
    __tablename__ = "airspace_assignments"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircrafts.aircraft_id"))
    flight_ref = Column(String, index=True)
    dep_arpt = Column(String)
    arr_arpt = Column(String)
    igtd = Column(String)
    fixes = Column(JSON)
    waypoints = Column(JSON)
    sectors = Column(JSON)
    airways = Column(JSON)
    centers = Column(JSON)
    aircraft = relationship("AircraftDBModel", back_populates="assignments")
