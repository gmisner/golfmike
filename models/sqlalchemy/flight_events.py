"""
Flight Events Database Model
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base
from sqlalchemy.orm import relationship


class FlightEventsDBModel(Base):
    """Flight events for status tracking and notifications"""

    __tablename__ = "flight_events"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)
    gufi = Column(String(50), nullable=False, index=True)
    event_type = Column(
        String(50), nullable=False, index=True
    )  # PLANNED, DEPARTED, IN_FLIGHT, ARRIVED, DIVERTED, CANCELLED
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_data = Column(JSONB)  # Additional event-specific data
    source_facility = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    aircraft = relationship("AircraftDBModel", back_populates="flight_events")


class TrackUpdatesDBModel(Base):
    """Real-time track updates for position tracking"""

    __tablename__ = "track_updates"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)
    gufi = Column(String(50), nullable=False, index=True)
    latitude = Column(String, nullable=False)  # Will be converted to DECIMAL in SQL
    longitude = Column(String, nullable=False)  # Will be converted to DECIMAL in SQL
    altitude = Column(Integer)  # in feet
    speed = Column(Integer)  # in knots
    heading = Column(Integer)  # in degrees
    time_at_position = Column(DateTime(timezone=True), nullable=False, index=True)
    source_facility = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    aircraft = relationship("AircraftDBModel", back_populates="track_updates")


class AircraftProfilesDBModel(Base):
    """Aircraft profiles for avatars and detailed information"""

    __tablename__ = "aircraft_profiles"

    aircraft_id = Column(String(50), primary_key=True)
    airline = Column(String(10))
    aircraft_type = Column(String(20))
    aircraft_category = Column(String(20))  # JET, TURBO, PISTON
    user_category = Column(String(30))  # COMMERCIAL, GENERAL AVIATION, CARGO, AIR TAXI
    avatar_url = Column(String(255))  # URL to aircraft avatar/image
    livery_colors = Column(JSONB)  # Store airline colors for custom avatars
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class FlightRoutesDBModel(Base):
    """Flight routes and waypoints"""

    __tablename__ = "flight_routes"

    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)
    gufi = Column(String(50), nullable=False, index=True)
    route_name = Column(String(100))
    waypoints = Column(JSONB)  # Array of waypoints with lat/long
    airways = Column(JSONB)  # Array of airways
    sectors = Column(JSONB)  # Array of ATC sectors
    route_of_flight = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    aircraft = relationship("AircraftDBModel", back_populates="flight_routes")
