from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, Index
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime


class UpcomingFlightDBModel(Base):
    """Class representing upcoming flight plans in the database"""

    __tablename__ = "upcoming_flights"
    
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(String(50), nullable=False, index=True)
    gufi = Column(String(50), unique=True, index=True)
    flight_reference = Column(String(50), index=True)
    
    # Flight details
    departure_airport = Column(String(10), index=True)
    arrival_airport = Column(String(10), index=True)
    departure_time = Column(DateTime, index=True)
    arrival_time = Column(DateTime, index=True)
    
    # Aircraft information
    aircraft_type = Column(String(50))
    aircraft_operator = Column(String(100))
    
    # Route information
    route_text = Column(Text)
    filed_route = Column(Text)
    
    # Status and metadata
    status = Column(String(50), default="PLANNED", index=True)  # PLANNED, ACTIVE, COMPLETED, CANCELLED
    source_facility = Column(String(50))
    source_timestamp = Column(DateTime)
    
    # Data source tracking
    data_source = Column(String(50), default="SOLACE")  # SOLACE, MANUAL, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional flight plan data
    flight_plan_data = Column(Text)  # Store raw XML or JSON data
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_upcoming_flights_aircraft_departure', 'aircraft_id', 'departure_time'),
        Index('idx_upcoming_flights_route', 'departure_airport', 'arrival_airport'),
        Index('idx_upcoming_flights_status_time', 'status', 'departure_time'),
    )
