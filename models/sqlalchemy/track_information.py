# models/sqlalchemy/track_information.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from models.base import Base
from sqlalchemy.orm import relationship


class TrackInformationDBModel(Base):
    __tablename__ = "track_information"

    # Primary key for the track information table
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking to the aircraft table (many track records can belong to one aircraft)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"))

    # Globally unique flight identifier
    gufi = Column(String)

    # Speed of the aircraft (in knots or another specified unit)
    speed = Column(Integer)

    # Altitude of the aircraft (in feet or another specified unit)
    altitude = Column(Integer)

    # Latitude in decimal format
    latitude = Column(String)

    # Longitude in decimal format
    longitude = Column(String)

    # Time at the current position of the aircraft
    time_at_position = Column(String)

    # Departure airport code (e.g., ICAO/IATA code)
    departure_airport = Column(String)

    # Arrival airport code (e.g., ICAO/IATA code)
    arrival_airport = Column(String)

    # Estimated time of departure (ETD)
    etd = Column(String)

    # Estimated time of arrival (ETA)
    eta = Column(String)

    # Diversion indicator status (indicates if the flight was diverted)
    diversion_indicator = Column(String)

    # RVSM (Reduced Vertical Separation Minimum) data attributes
    rvsm_data = Column(JSON)

    # Next position of the aircraft with latitude and longitude information
    next_position = Column(JSON)

    # List of flight traversal fixes (points along the route)
    fixes = Column(JSON)

    # List of waypoints with latitude, longitude, and elapsed time
    waypoints = Column(JSON)

    # List of air traffic control sectors the aircraft has traversed or will traverse
    sectors = Column(JSON)

    # Route of flight description (a textual representation of the route)
    route_of_flight = Column(String)

    # Relationship to the AircraftDBModel (defines back reference for bidirectional relationship)
    aircraft = relationship("AircraftDBModel", back_populates="track_information")
