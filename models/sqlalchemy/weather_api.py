"""
SQLAlchemy models for AviationWeather.gov API data

This module defines database models for storing weather data fetched from
the AviationWeather.gov API, separate from the ITWS real-time data.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()


class WeatherStationAPI(Base):
    """Weather station information from AviationWeather.gov API"""

    __tablename__ = "weather_stations_api"

    id = Column(Integer, primary_key=True)
    icao_id = Column(String(4), unique=True, nullable=False, index=True)
    iata_id = Column(String(3), index=True)
    faa_id = Column(String(4), index=True)
    site_name = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    elevation_ft = Column(Integer)
    state = Column(String(2))
    country = Column(String(2))
    priority = Column(Integer)
    site_types = Column(JSONB)  # Array of site types like ['METAR', 'TAF']
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_weather_stations_api_location", "latitude", "longitude"),
        Index("idx_weather_stations_api_state", "state"),
    )


class METARDataAPI(Base):
    """METAR data from AviationWeather.gov API"""

    __tablename__ = "metar_data_api"

    id = Column(Integer, primary_key=True)
    station_id = Column(String(4), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)
    raw_text = Column(Text)

    # Wind data
    wind_direction = Column(Integer)  # degrees
    wind_speed = Column(Integer)  # knots
    wind_gust = Column(Integer)  # knots

    # Visibility
    visibility = Column(String(10))  # statute miles (can be "10+" etc)
    visibility_units = Column(String(10))

    # Temperature and pressure
    temperature = Column(Float)  # Celsius
    dewpoint = Column(Float)  # Celsius
    altimeter = Column(Float)  # inches of mercury

    # Flight category
    flight_category = Column(String(10))  # VFR, MVFR, IFR, LIFR

    # Sky conditions (JSON array)
    sky_conditions = Column(JSONB)

    # Weather phenomena (JSON array)
    weather_phenomena = Column(JSONB)

    # Additional data
    quality_flags = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_metar_api_station_time", "station_id", "observation_time"),
        Index("idx_metar_api_observation_time", "observation_time"),
        Index("idx_metar_api_flight_category", "flight_category"),
    )


class TAFDataAPI(Base):
    """TAF data from AviationWeather.gov API"""

    __tablename__ = "taf_data_api"

    id = Column(Integer, primary_key=True)
    station_id = Column(String(4), nullable=False, index=True)
    issue_time = Column(DateTime, nullable=False, index=True)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=False, index=True)
    raw_text = Column(Text)

    # Forecast periods (JSON array)
    forecast_periods = Column(JSONB)

    # Sky conditions (JSON array)
    sky_conditions = Column(JSONB)

    # Weather phenomena (JSON array)
    weather_phenomena = Column(JSONB)

    # Additional data
    quality_flags = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_taf_api_station_issue", "station_id", "issue_time"),
        Index("idx_taf_api_valid_period", "valid_from", "valid_to"),
        Index("idx_taf_api_issue_time", "issue_time"),
    )


class PIREPDataAPI(Base):
    """PIREP data from AviationWeather.gov API"""

    __tablename__ = "pirep_data_api"

    id = Column(Integer, primary_key=True)
    receipt_time = Column(DateTime, nullable=False, index=True)
    observation_time = Column(DateTime, index=True)
    quality_control_flags = Column(Integer)

    # Aircraft information
    aircraft_ref = Column(String(10))
    aircraft_type = Column(String(20))

    # Location
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    altitude_ft_msl = Column(Integer)
    flight_level = Column(String(10))
    flight_level_type = Column(String(10))

    # Weather conditions
    sky_condition = Column(String(50))
    visibility = Column(String(20))
    weather_string = Column(String(100))
    temperature = Column(Float)

    # Wind
    wind_direction = Column(Integer)
    wind_speed = Column(Integer)
    vertical_gust = Column(Integer)

    # Turbulence
    turbulence_base_1 = Column(Integer)
    turbulence_top_1 = Column(Integer)
    turbulence_intensity_1 = Column(String(20))
    turbulence_type_1 = Column(String(20))
    turbulence_frequency_1 = Column(String(20))

    turbulence_base_2 = Column(Integer)
    turbulence_top_2 = Column(Integer)
    turbulence_intensity_2 = Column(String(20))
    turbulence_type_2 = Column(String(20))
    turbulence_frequency_2 = Column(String(20))

    # Icing
    icing_base_1 = Column(Integer)
    icing_top_1 = Column(Integer)
    icing_intensity_1 = Column(String(20))
    icing_type_1 = Column(String(20))

    icing_base_2 = Column(Integer)
    icing_top_2 = Column(Integer)
    icing_intensity_2 = Column(String(20))
    icing_type_2 = Column(String(20))

    # Additional data
    pirep_type = Column(String(20))  # PIREP, Urgent PIREP, AIREP, AMDAR
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_pirep_api_receipt_time", "receipt_time"),
        Index("idx_pirep_api_location", "latitude", "longitude"),
        Index("idx_pirep_api_altitude", "altitude_ft_msl"),
        Index("idx_pirep_api_aircraft", "aircraft_ref"),
    )


class WeatherAlertAPI(Base):
    """Weather alerts from AviationWeather.gov API (AIRMETs, SIGMETs, etc.)"""

    __tablename__ = "weather_alerts_api"

    id = Column(Integer, primary_key=True)
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)

    # Alert classification
    severity = Column(String(20))  # LOW, MODERATE, HIGH, EXTREME
    urgency = Column(String(20))  # IMMEDIATE, EXPECTED, FUTURE, PAST

    # Timing
    valid_from = Column(DateTime, index=True)
    valid_until = Column(DateTime, index=True)
    issued_at = Column(DateTime, index=True)

    # Content
    raw_text = Column(Text)
    summary = Column(Text)
    description = Column(Text)

    # Geographic information
    affected_area = Column(JSONB)  # Geographic bounds, coordinates, etc.
    affected_airports = Column(JSONB)  # Array of affected airport codes

    # Weather phenomena
    weather_phenomena = Column(JSONB)

    # Altitude information
    altitude_floor = Column(Integer)
    altitude_ceiling = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_cancelled = Column(Boolean, default=False)

    # Additional metadata
    source = Column(String(50), default="AviationWeather.gov")
    quality_flags = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_weather_alerts_api_type", "alert_type"),
        Index("idx_weather_alerts_api_valid_period", "valid_from", "valid_until"),
        Index("idx_weather_alerts_api_active", "is_active"),
        Index("idx_weather_alerts_api_issued", "issued_at"),
    )


class WeatherObservationAPI(Base):
    """General weather observations from AviationWeather.gov API"""

    __tablename__ = "weather_observations_api"

    id = Column(Integer, primary_key=True)
    station_id = Column(String(4), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)

    # Basic weather data
    temperature = Column(Float)
    dewpoint = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)

    # Wind
    wind_direction = Column(Integer)
    wind_speed = Column(Integer)
    wind_gust = Column(Integer)

    # Visibility and ceiling
    visibility = Column(Float)
    ceiling = Column(Integer)
    ceiling_type = Column(String(20))

    # Precipitation
    precipitation_type = Column(String(20))
    precipitation_amount = Column(Float)

    # Raw data and quality
    raw_data = Column(JSONB)
    quality_flags = Column(JSONB)
    data_source = Column(String(50), default="AviationWeather.gov")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_weather_obs_api_station_time", "station_id", "observation_time"),
        Index("idx_weather_obs_api_observation_time", "observation_time"),
        Index("idx_weather_obs_api_data_source", "data_source"),
    )
