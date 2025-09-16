"""
Pydantic models for weather data validation and serialization
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class WeatherStationType(str, Enum):
    """Types of weather stations"""

    METAR = "METAR"
    TAF = "TAF"
    AWOS = "AWOS"
    ASOS = "ASOS"
    ATIS = "ATIS"


class FlightCategory(str, Enum):
    """Flight categories based on weather conditions"""

    VFR = "VFR"  # Visual Flight Rules
    MVFR = "MVFR"  # Marginal Visual Flight Rules
    IFR = "IFR"  # Instrument Flight Rules
    LIFR = "LIFR"  # Low Instrument Flight Rules


class WeatherPhenomenon(BaseModel):
    """Weather phenomenon (e.g., RA, SN, FG)"""

    code: str = Field(..., description="Weather phenomenon code")
    intensity: Optional[str] = Field(
        None, description="Intensity modifier (-, +, or None)"
    )
    descriptor: Optional[str] = Field(None, description="Descriptor (SH, TS, etc.)")
    proximity: Optional[str] = Field(None, description="Proximity modifier (VC, etc.)")


class SkyCondition(BaseModel):
    """Sky condition information"""

    coverage: str = Field(..., description="Sky coverage (CLR, FEW, SCT, BKN, OVC)")
    altitude: Optional[int] = Field(None, description="Cloud base altitude in feet")
    cloud_type: Optional[str] = Field(None, description="Cloud type (CB, TCU, etc.)")


class WeatherStationModel(BaseModel):
    """Weather station information"""

    station_id: str = Field(..., description="ICAO station identifier")
    station_name: Optional[str] = Field(None, description="Station name")
    station_type: Optional[WeatherStationType] = Field(None, description="Station type")
    latitude: Optional[float] = Field(None, description="Latitude in decimal degrees")
    longitude: Optional[float] = Field(None, description="Longitude in decimal degrees")
    elevation: Optional[float] = Field(None, description="Elevation in feet")
    state: Optional[str] = Field(None, description="State code")
    country: Optional[str] = Field(None, description="Country code")

    class Config:
        from_attributes = True


class METARModel(BaseModel):
    """METAR (Meteorological Aerodrome Report) data model"""

    station_id: str = Field(..., description="ICAO station identifier")
    observation_time: datetime = Field(..., description="Observation time")
    raw_text: Optional[str] = Field(None, description="Original METAR text")

    # Wind data
    wind_direction: Optional[int] = Field(
        None, ge=0, le=360, description="Wind direction in degrees"
    )
    wind_speed: Optional[int] = Field(None, ge=0, description="Wind speed in knots")
    wind_gust: Optional[int] = Field(None, ge=0, description="Wind gust in knots")

    # Visibility
    visibility: Optional[float] = Field(
        None, ge=0, description="Visibility in statute miles"
    )
    visibility_units: Optional[str] = Field(None, description="Visibility units")

    # Sky conditions
    sky_conditions: Optional[List[SkyCondition]] = Field(
        None, description="Sky conditions"
    )

    # Temperature and pressure
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    dewpoint: Optional[float] = Field(None, description="Dewpoint in Celsius")
    altimeter: Optional[float] = Field(
        None, ge=28.0, le=31.0, description="Altimeter setting in inches"
    )

    # Weather phenomena
    weather_phenomena: Optional[List[WeatherPhenomenon]] = Field(
        None, description="Weather phenomena"
    )

    # Flight category
    flight_category: Optional[FlightCategory] = Field(
        None, description="Flight category"
    )

    # Additional data
    sea_level_pressure: Optional[float] = Field(
        None, description="Sea level pressure in millibars"
    )
    pressure_tendency: Optional[float] = Field(
        None, description="Pressure tendency in millibars"
    )

    class Config:
        from_attributes = True


class TAFPeriod(BaseModel):
    """TAF forecast period"""

    valid_from: datetime = Field(..., description="Valid from time")
    valid_until: datetime = Field(..., description="Valid until time")

    # Wind data
    wind_direction: Optional[int] = Field(
        None, ge=0, le=360, description="Wind direction in degrees"
    )
    wind_speed: Optional[int] = Field(None, ge=0, description="Wind speed in knots")
    wind_gust: Optional[int] = Field(None, ge=0, description="Wind gust in knots")

    # Visibility
    visibility: Optional[float] = Field(
        None, ge=0, description="Visibility in statute miles"
    )
    visibility_units: Optional[str] = Field(None, description="Visibility units")

    # Sky conditions
    sky_conditions: Optional[List[SkyCondition]] = Field(
        None, description="Sky conditions"
    )

    # Weather phenomena
    weather_phenomena: Optional[List[WeatherPhenomenon]] = Field(
        None, description="Weather phenomena"
    )

    # Flight category
    flight_category: Optional[FlightCategory] = Field(
        None, description="Flight category"
    )

    # Probability
    probability: Optional[int] = Field(
        None, ge=0, le=100, description="Probability percentage"
    )


class TAFModel(BaseModel):
    """TAF (Terminal Aerodrome Forecast) data model"""

    station_id: str = Field(..., description="ICAO station identifier")
    issue_time: datetime = Field(..., description="Issue time")
    valid_from: datetime = Field(..., description="Valid from time")
    valid_to: datetime = Field(..., description="Valid until time")
    raw_text: Optional[str] = Field(None, description="Original TAF text")

    # Forecast periods
    forecast_periods: Optional[List[TAFPeriod]] = Field(
        None, description="Forecast periods"
    )

    class Config:
        from_attributes = True


class NOTAMType(str, Enum):
    """NOTAM types"""

    NOTAM = "NOTAM"
    SNOWTAM = "SNOWTAM"
    ASHTAM = "ASHTAM"
    FIR = "FIR"
    UIR = "UIR"


class NOTAMPriority(str, Enum):
    """NOTAM priority levels"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NOTAMCategory(str, Enum):
    """NOTAM categories"""

    AIRPORT = "AIRPORT"
    NAVIGATION = "NAVIGATION"
    WEATHER = "WEATHER"
    AIRSPACE = "AIRSPACE"
    COMMUNICATION = "COMMUNICATION"


class NOTAMModel(BaseModel):
    """NOTAM (Notice to Airmen) data model"""

    notam_id: str = Field(..., description="Unique NOTAM identifier")
    notam_number: Optional[str] = Field(None, description="NOTAM number")

    # Location
    location_identifier: str = Field(..., description="Airport/airspace identifier")
    location_type: Optional[str] = Field(None, description="Location type")
    affected_airspace: Optional[List[Dict[str, Any]]] = Field(
        None, description="Affected airspace"
    )

    # Timing
    effective_from: datetime = Field(..., description="Effective from time")
    effective_until: Optional[datetime] = Field(
        None, description="Effective until time"
    )

    # Content
    raw_text: Optional[str] = Field(None, description="Original NOTAM text")
    summary: Optional[str] = Field(None, description="Human-readable summary")
    description: Optional[str] = Field(None, description="Detailed description")

    # Classification
    notam_type: Optional[NOTAMType] = Field(None, description="NOTAM type")
    priority: Optional[NOTAMPriority] = Field(None, description="Priority level")
    category: Optional[NOTAMCategory] = Field(None, description="Category")

    # Status
    is_active: bool = Field(True, description="Whether NOTAM is active")
    is_cancelled: bool = Field(False, description="Whether NOTAM is cancelled")

    # Additional data
    coordinates: Optional[Dict[str, Any]] = Field(
        None, description="Geographic coordinates"
    )
    altitude_floor: Optional[int] = Field(None, description="Altitude floor in feet")
    altitude_ceiling: Optional[int] = Field(
        None, description="Altitude ceiling in feet"
    )

    class Config:
        from_attributes = True


class WeatherAlertType(str, Enum):
    """Weather alert types"""

    SIGMET = "SIGMET"
    AIRMET = "AIRMET"
    CONVECTIVE_SIGMET = "CONVECTIVE_SIGMET"
    CENTER_WEATHER_ADVISORY = "CENTER_WEATHER_ADVISORY"


class WeatherAlertSeverity(str, Enum):
    """Weather alert severity levels"""

    SEVERE = "SEVERE"
    MODERATE = "MODERATE"
    MINOR = "MINOR"


class WeatherAlertUrgency(str, Enum):
    """Weather alert urgency levels"""

    IMMEDIATE = "IMMEDIATE"
    EXPECTED = "EXPECTED"
    FUTURE = "FUTURE"


class WeatherAlertModel(BaseModel):
    """Weather alert data model"""

    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: WeatherAlertType = Field(..., description="Alert type")
    severity: Optional[WeatherAlertSeverity] = Field(None, description="Severity level")
    urgency: Optional[WeatherAlertUrgency] = Field(None, description="Urgency level")

    # Location
    affected_area: Optional[Dict[str, Any]] = Field(
        None, description="Affected geographic area"
    )
    affected_airports: Optional[List[str]] = Field(
        None, description="Affected airport codes"
    )

    # Timing
    valid_from: datetime = Field(..., description="Valid from time")
    valid_until: Optional[datetime] = Field(None, description="Valid until time")
    issued_at: datetime = Field(..., description="Issue time")

    # Content
    raw_text: Optional[str] = Field(None, description="Original alert text")
    summary: Optional[str] = Field(None, description="Human-readable summary")
    description: Optional[str] = Field(None, description="Detailed description")

    # Weather conditions
    weather_phenomena: Optional[List[WeatherPhenomenon]] = Field(
        None, description="Weather phenomena"
    )
    altitude_floor: Optional[int] = Field(None, description="Altitude floor in feet")
    altitude_ceiling: Optional[int] = Field(
        None, description="Altitude ceiling in feet"
    )

    # Status
    is_active: bool = Field(True, description="Whether alert is active")
    is_cancelled: bool = Field(False, description="Whether alert is cancelled")

    class Config:
        from_attributes = True


class WeatherObservationModel(BaseModel):
    """Weather observation data model"""

    station_id: str = Field(..., description="Station identifier")
    observation_time: datetime = Field(..., description="Observation time")

    # Basic measurements
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    dewpoint: Optional[float] = Field(None, description="Dewpoint in Celsius")
    humidity: Optional[float] = Field(
        None, ge=0, le=100, description="Humidity percentage"
    )
    pressure: Optional[float] = Field(None, description="Pressure in millibars")
    wind_direction: Optional[int] = Field(
        None, ge=0, le=360, description="Wind direction in degrees"
    )
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in knots")
    wind_gust: Optional[float] = Field(None, ge=0, description="Wind gust in knots")

    # Visibility and ceiling
    visibility: Optional[float] = Field(
        None, ge=0, description="Visibility in statute miles"
    )
    ceiling: Optional[int] = Field(None, ge=0, description="Ceiling in feet")
    ceiling_type: Optional[str] = Field(None, description="Ceiling type (AGL, MSL)")

    # Precipitation
    precipitation_type: Optional[str] = Field(None, description="Precipitation type")
    precipitation_rate: Optional[float] = Field(
        None, ge=0, description="Precipitation rate in inches/hour"
    )
    precipitation_accumulation: Optional[float] = Field(
        None, ge=0, description="Precipitation accumulation in inches"
    )

    # Additional data
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original sensor data")
    data_source: Optional[str] = Field(None, description="Data source")
    quality_flags: Optional[Dict[str, Any]] = Field(
        None, description="Data quality indicators"
    )

    class Config:
        from_attributes = True


