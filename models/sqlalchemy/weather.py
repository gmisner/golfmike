"""
Weather Database Models for SQLAlchemy
Handles METAR, TAF, NOTAMs, and other weather data
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base


class WeatherStation(Base):
    """Weather station information (airports, AWOS, etc.)"""

    __tablename__ = "weather_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(
        String(10), unique=True, nullable=False, index=True
    )  # ICAO code
    station_name = Column(String(100))
    station_type = Column(String(20))  # METAR, TAF, AWOS, ASOS
    latitude = Column(Float)
    longitude = Column(Float)
    elevation = Column(Float)  # in feet
    state = Column(String(2))
    country = Column(String(2))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (Index("idx_weather_stations_location", "latitude", "longitude"),)


class METARData(Base):
    """METAR (Meteorological Aerodrome Report) data"""

    __tablename__ = "metar_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(10), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)
    raw_text = Column(Text)  # Original METAR text

    # Basic weather conditions
    wind_direction = Column(Integer)  # degrees
    wind_speed = Column(Integer)  # knots
    wind_gust = Column(Integer)  # knots
    visibility = Column(Float)  # statute miles
    visibility_units = Column(String(10))

    # Sky conditions
    sky_conditions = Column(JSONB)  # Array of sky condition objects

    # Temperature and pressure
    temperature = Column(Float)  # Celsius
    dewpoint = Column(Float)  # Celsius
    altimeter = Column(Float)  # inches of mercury

    # Weather phenomena
    weather_phenomena = Column(JSONB)  # Array of weather codes

    # Additional data
    flight_category = Column(String(1))  # VFR, MVFR, IFR, LIFR
    sea_level_pressure = Column(Float)  # millibars
    pressure_tendency = Column(Float)  # millibars

    # Metadata
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (
        Index("idx_metar_station_time", "station_id", "observation_time"),
        Index("idx_metar_observation_time", "observation_time"),
    )


class TAFData(Base):
    """TAF (Terminal Aerodrome Forecast) data"""

    __tablename__ = "taf_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(10), nullable=False, index=True)
    issue_time = Column(DateTime, nullable=False, index=True)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=False, index=True)
    raw_text = Column(Text)  # Original TAF text

    # Forecast periods
    forecast_periods = Column(JSONB)  # Array of forecast period objects

    # Basic forecast data
    wind_direction = Column(Integer)  # degrees
    wind_speed = Column(Integer)  # knots
    wind_gust = Column(Integer)  # knots
    visibility = Column(Float)  # statute miles
    visibility_units = Column(String(10))

    # Sky conditions
    sky_conditions = Column(JSONB)  # Array of sky condition objects

    # Weather phenomena
    weather_phenomena = Column(JSONB)  # Array of weather codes

    # Additional data
    flight_category = Column(String(1))  # VFR, MVFR, IFR, LIFR
    probability = Column(Integer)  # Probability percentage

    # Metadata
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (
        Index("idx_taf_station_time", "station_id", "issue_time"),
        Index("idx_taf_valid_period", "valid_from", "valid_to"),
    )


class NOTAMData(Base):
    """NOTAM (Notice to Airmen) data"""

    __tablename__ = "notam_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notam_id = Column(String(50), unique=True, nullable=False, index=True)
    notam_number = Column(String(20), index=True)

    # Location and scope
    location_identifier = Column(String(10), index=True)  # Airport/airspace identifier
    location_type = Column(String(20))  # AIRPORT, AIRSPACE, NAVIGATION, etc.
    affected_airspace = Column(JSONB)  # Array of affected airspace objects

    # Timing
    effective_from = Column(DateTime, nullable=False, index=True)
    effective_until = Column(DateTime, index=True)
    created_at = Column(DateTime)

    # Content
    raw_text = Column(Text)  # Original NOTAM text
    summary = Column(Text)  # Human-readable summary
    description = Column(Text)  # Detailed description

    # Classification
    notam_type = Column(String(20))  # NOTAM, SNOWTAM, ASHTAM, etc.
    priority = Column(String(10))  # HIGH, MEDIUM, LOW
    category = Column(String(20))  # AIRPORT, NAVIGATION, WEATHER, etc.

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_cancelled = Column(Boolean, default=False)

    # Additional data
    coordinates = Column(JSONB)  # Geographic coordinates if applicable
    altitude_floor = Column(Integer)  # feet
    altitude_ceiling = Column(Integer)  # feet

    # Metadata
    updated_at = Column(DateTime)

    __table_args__ = (
        Index("idx_notam_location_time", "location_identifier", "effective_from"),
        Index("idx_notam_effective_period", "effective_from", "effective_until"),
        Index("idx_notam_active", "is_active", "effective_until"),
    )


class WeatherAlert(Base):
    """Weather alerts and warnings"""

    __tablename__ = "weather_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), unique=True, nullable=False, index=True)

    # Alert details
    alert_type = Column(String(20), nullable=False, index=True)  # SIGMET, AIRMET, etc.
    severity = Column(String(10))  # SEVERE, MODERATE, MINOR
    urgency = Column(String(10))  # IMMEDIATE, EXPECTED, FUTURE

    # Location and scope
    affected_area = Column(JSONB)  # Geographic area description
    affected_airports = Column(JSONB)  # Array of affected airport codes

    # Timing
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_until = Column(DateTime, index=True)
    issued_at = Column(DateTime, nullable=False, index=True)

    # Content
    raw_text = Column(Text)  # Original alert text
    summary = Column(Text)  # Human-readable summary
    description = Column(Text)  # Detailed description

    # Weather conditions
    weather_phenomena = Column(JSONB)  # Array of weather conditions
    altitude_floor = Column(Integer)  # feet
    altitude_ceiling = Column(Integer)  # feet

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_cancelled = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (
        Index("idx_weather_alert_type_time", "alert_type", "valid_from"),
        Index("idx_weather_alert_valid_period", "valid_from", "valid_until"),
        Index("idx_weather_alert_active", "is_active", "valid_until"),
    )


class WeatherObservation(Base):
    """General weather observations and sensor data"""

    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(10), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)

    # Basic measurements
    temperature = Column(Float)  # Celsius
    dewpoint = Column(Float)  # Celsius
    humidity = Column(Float)  # percentage
    pressure = Column(Float)  # millibars
    wind_direction = Column(Integer)  # degrees
    wind_speed = Column(Float)  # knots
    wind_gust = Column(Float)  # knots

    # Visibility and ceiling
    visibility = Column(Float)  # statute miles
    ceiling = Column(Integer)  # feet
    ceiling_type = Column(String(10))  # AGL, MSL

    # Precipitation
    precipitation_type = Column(String(20))
    precipitation_rate = Column(Float)  # inches per hour
    precipitation_accumulation = Column(Float)  # inches

    # Additional data
    raw_data = Column(JSONB)  # Original sensor data
    data_source = Column(String(20))  # AWOS, ASOS, METAR, etc.
    quality_flags = Column(JSONB)  # Data quality indicators

    # Metadata
    created_at = Column(DateTime)

    __table_args__ = (
        Index("idx_weather_obs_station_time", "station_id", "observation_time"),
        Index("idx_weather_obs_time", "observation_time"),
    )


