"""
Hub-and-spoke flight schema: flights(gufi) is the anchor for route, track, and alerts.
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Float,
    ForeignKey,
    Boolean,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base import Base


class FlightsDBModel(Base):
    __tablename__ = "flights"

    gufi = Column(String(50), primary_key=True)
    aircraft_id = Column(
        String(50), ForeignKey("aircraft.aircraft_id"), nullable=False, index=True
    )
    flight_reference = Column(String(50))
    departure_airport = Column(String(10))
    arrival_airport = Column(String(10))
    scheduled_departure = Column(DateTime(timezone=True))
    scheduled_arrival = Column(DateTime(timezone=True))
    current_status = Column(String(50), default="PLANNED", index=True)
    source_timestamp = Column(DateTime(timezone=True))
    route_text = Column(Text)
    current_beacon_code = Column(String(10))
    fdps_flight_status = Column(String(50), index=True)
    coordination_time = Column(DateTime(timezone=True), index=True)
    coordination_fix = Column(String(20))
    coordination_distance_nm = Column(Float)
    coordination_radial_deg = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    aircraft = relationship("AircraftDBModel", back_populates="flights")
    flight_plan = relationship(
        "FlightPlanDBModel",
        back_populates="flight",
        uselist=False,
    )
    route_assignments = relationship(
        "RouteAssignmentDBModel", back_populates="flight", cascade="all, delete-orphan"
    )
    track_updates = relationship(
        "TrackUpdatesDBModel", back_populates="flight", cascade="all, delete-orphan"
    )
    flight_alerts = relationship(
        "FlightAlertDBModel", back_populates="flight", cascade="all, delete-orphan"
    )


class RouteAssignmentDBModel(Base):
    __tablename__ = "route_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gufi = Column(
        String(50),
        ForeignKey("flights.gufi", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_altitude = Column(Integer)
    assigned_speed = Column(Integer)
    route_data = Column(JSONB)
    etd = Column(DateTime(timezone=True))
    eta = Column(DateTime(timezone=True))
    source_facility = Column(String(50))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    flight = relationship("FlightsDBModel", back_populates="route_assignments")
    waypoints = relationship(
        "RouteWaypointDBModel",
        back_populates="route_assignment",
        cascade="all, delete-orphan",
    )


class RouteWaypointDBModel(Base):
    __tablename__ = "route_waypoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_assignment_id = Column(
        Integer,
        ForeignKey("route_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number = Column(Integer, nullable=False)
    waypoint_type = Column(String(20))
    name = Column(String(50))
    latitude = Column(String(20))
    longitude = Column(String(20))
    elapsed_time = Column(Integer)
    altitude = Column(Integer)

    route_assignment = relationship(
        "RouteAssignmentDBModel", back_populates="waypoints"
    )


class FlightAlertDBModel(Base):
    __tablename__ = "flight_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gufi = Column(
        String(50),
        ForeignKey("flights.gufi", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="INFO", index=True)
    message = Column(Text)
    alert_data = Column(JSONB)
    acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    flight = relationship("FlightsDBModel", back_populates="flight_alerts")
