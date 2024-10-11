from sqlalchemy import Column, String, Integer
from models.base import Base
from sqlalchemy.orm import relationship


class AircraftDBModel(Base):
    __tablename__ = "aircraft"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String, unique=True, index=True)
    airline = Column(String)
    aircraft_category = Column(String)
    user_category = Column(String)

    # Relationships
    flight_plan = relationship("FlightPlanDBModel", back_populates="aircraft")
    tmi_updates = relationship("TmiUpdatesDBModel", back_populates="aircraft")
    fxa_flight = relationship("FxaFlightDBModel", back_populates="aircraft")
    track_information = relationship(
        "TrackInformationDBModel", back_populates="aircraft"
    )
    status_updates = relationship("StatusDBModel", back_populates="aircraft")

    # This should match the relationship in FlightSectorsDBModel
    airspace_assignments = relationship(
        "FlightSectorsDBModel", back_populates="aircraft"
    )
