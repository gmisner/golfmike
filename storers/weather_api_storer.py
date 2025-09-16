"""
Weather API Data Storer

This module handles storing weather data from the AviationWeather.gov API
into separate database tables from the ITWS real-time data.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from db_config import SessionLocal
from models.sqlalchemy.weather_api import (
    WeatherStationAPI,
    METARDataAPI,
    TAFDataAPI,
    PIREPDataAPI,
    WeatherAlertAPI,
    WeatherObservationAPI,
)
from utils.logger import logger


class WeatherAPIStorer:
    """Stores weather data from AviationWeather.gov API"""

    def __init__(self):
        self.logger = logger

    def store_metar_data(self, metar_data: List[Dict[str, Any]]) -> int:
        """Store METAR data in the API-specific table"""
        stored_count = 0
        session = SessionLocal()

        try:
            for metar in metar_data:
                try:
                    # Check if METAR already exists
                    existing = (
                        session.query(METARDataAPI)
                        .filter(
                            METARDataAPI.station_id == metar.get("icaoId"),
                            METARDataAPI.observation_time
                            == self._parse_datetime(metar.get("obsTime")),
                        )
                        .first()
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create new METAR record
                    metar_record = METARDataAPI(
                        station_id=metar.get("icaoId"),
                        observation_time=self._parse_datetime(metar.get("obsTime")),
                        raw_text=metar.get("rawOb"),
                        wind_direction=metar.get("wdir"),
                        wind_speed=metar.get("wspd"),
                        wind_gust=metar.get("wspdGust"),
                        visibility=metar.get("visib"),
                        visibility_units=metar.get("visibUnit"),
                        temperature=metar.get("temp"),
                        dewpoint=metar.get("dewp"),
                        altimeter=metar.get("altim"),
                        flight_category=metar.get("fltlvl"),
                        sky_conditions=self._parse_sky_conditions(
                            metar.get("skyc1", [])
                        ),
                        weather_phenomena=self._parse_weather_phenomena(
                            metar.get("wxcodes", [])
                        ),
                        quality_flags=metar.get("qualityControlFlags"),
                    )

                    session.add(metar_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Error storing METAR {metar.get('icaoId')}: {e}")
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new METAR records in API table")
            return stored_count

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error storing METAR data: {e}")
            return 0
        finally:
            session.close()

    def store_taf_data(self, taf_data: List[Dict[str, Any]]) -> int:
        """Store TAF data in the API-specific table"""
        stored_count = 0
        session = SessionLocal()

        try:
            for taf in taf_data:
                try:
                    # Check if TAF already exists
                    existing = (
                        session.query(TAFDataAPI)
                        .filter(
                            TAFDataAPI.station_id == taf.get("icaoId"),
                            TAFDataAPI.issue_time
                            == self._parse_datetime(taf.get("issueTime")),
                        )
                        .first()
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create new TAF record
                    taf_record = TAFDataAPI(
                        station_id=taf.get("icaoId"),
                        issue_time=self._parse_datetime(taf.get("issueTime")),
                        valid_from=self._parse_datetime(taf.get("validTimeFrom")),
                        valid_to=self._parse_datetime(taf.get("validTimeTo")),
                        raw_text=taf.get("rawTAF"),
                        forecast_periods=self._parse_forecast_periods(
                            taf.get("forecast", [])
                        ),
                        sky_conditions=self._parse_sky_conditions(taf.get("skyc1", [])),
                        weather_phenomena=self._parse_weather_phenomena(
                            taf.get("wxcodes", [])
                        ),
                        quality_flags=taf.get("qualityControlFlags"),
                    )

                    session.add(taf_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Error storing TAF {taf.get('icaoId')}: {e}")
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new TAF records in API table")
            return stored_count

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error storing TAF data: {e}")
            return 0
        finally:
            session.close()

    def store_pirep_data(self, pirep_data: List[Dict[str, Any]]) -> int:
        """Store PIREP data in the API-specific table"""
        stored_count = 0
        session = SessionLocal()

        try:
            for pirep in pirep_data:
                try:
                    # Check if PIREP already exists
                    existing = (
                        session.query(PIREPDataAPI)
                        .filter(
                            PIREPDataAPI.receipt_time
                            == self._parse_datetime(pirep.get("receiptTime")),
                            PIREPDataAPI.latitude == pirep.get("lat"),
                            PIREPDataAPI.longitude == pirep.get("lon"),
                        )
                        .first()
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create new PIREP record
                    pirep_record = PIREPDataAPI(
                        receipt_time=self._parse_datetime(pirep.get("receiptTime")),
                        observation_time=self._parse_datetime(pirep.get("obsTime")),
                        quality_control_flags=pirep.get("qcField"),
                        aircraft_ref=pirep.get("acType"),
                        aircraft_type=pirep.get("acType"),
                        latitude=pirep.get("lat"),
                        longitude=pirep.get("lon"),
                        altitude_ft_msl=pirep.get("fltLvl"),
                        flight_level=pirep.get("fltLvl"),
                        flight_level_type=pirep.get("fltLvlType"),
                        sky_condition=pirep.get("clouds"),
                        visibility=pirep.get("visib"),
                        weather_string=pirep.get("wxString"),
                        temperature=pirep.get("temp"),
                        wind_direction=pirep.get("wdir"),
                        wind_speed=pirep.get("wspd"),
                        vertical_gust=pirep.get("vertGust"),
                        pirep_type=pirep.get("pirepType"),
                        raw_text=pirep.get("rawOb"),
                    )

                    # Parse turbulence data if available
                    if pirep.get("tbBas1"):
                        pirep_record.turbulence_base_1 = pirep.get("tbBas1")
                        pirep_record.turbulence_top_1 = pirep.get("tbTop1")
                        pirep_record.turbulence_intensity_1 = pirep.get("tbInt1")
                        pirep_record.turbulence_type_1 = pirep.get("tbType1")
                        pirep_record.turbulence_frequency_1 = pirep.get("tbFreq1")

                    if pirep.get("tbBas2"):
                        pirep_record.turbulence_base_2 = pirep.get("tbBas2")
                        pirep_record.turbulence_top_2 = pirep.get("tbTop2")
                        pirep_record.turbulence_intensity_2 = pirep.get("tbInt2")
                        pirep_record.turbulence_type_2 = pirep.get("tbType2")
                        pirep_record.turbulence_frequency_2 = pirep.get("tbFreq2")

                    # Parse icing data if available
                    if pirep.get("icgBas1"):
                        pirep_record.icing_base_1 = pirep.get("icgBas1")
                        pirep_record.icing_top_1 = pirep.get("icgTop1")
                        pirep_record.icing_intensity_1 = pirep.get("icgInt1")
                        pirep_record.icing_type_1 = pirep.get("icgType1")

                    if pirep.get("icgBas2"):
                        pirep_record.icing_base_2 = pirep.get("icgBas2")
                        pirep_record.icing_top_2 = pirep.get("icgTop2")
                        pirep_record.icing_intensity_2 = pirep.get("icgInt2")
                        pirep_record.icing_type_2 = pirep.get("icgType2")

                    session.add(pirep_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Error storing PIREP: {e}")
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new PIREP records in API table")
            return stored_count

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error storing PIREP data: {e}")
            return 0
        finally:
            session.close()

    def store_weather_alert_data(self, alert_data: List[Dict[str, Any]]) -> int:
        """Store weather alert data in the API-specific table"""
        stored_count = 0
        session = SessionLocal()

        try:
            for i, alert in enumerate(alert_data):
                try:
                    # Create unique alert ID with index to prevent duplicates
                    alert_id = f"AWS_{alert.get('hazard', 'UNKNOWN')}_{alert.get('validTimeFrom', 'UNKNOWN')}_{i}"

                    # Check if alert already exists
                    existing = (
                        session.query(WeatherAlertAPI)
                        .filter(WeatherAlertAPI.alert_id == alert_id)
                        .first()
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create new alert record
                    alert_record = WeatherAlertAPI(
                        alert_id=alert_id,
                        alert_type=f"AWS_{alert.get('hazard', 'UNKNOWN')}",
                        severity="MODERATE",  # Default severity
                        urgency="EXPECTED",  # Default urgency
                        valid_from=self._parse_datetime(alert.get("validTimeFrom")),
                        valid_until=self._parse_datetime(alert.get("validTimeTo")),
                        issued_at=self._parse_datetime(alert.get("issueTime")),
                        raw_text=alert.get("rawSigmet"),
                        summary=f"{alert.get('hazard', 'Unknown')} alert for {alert.get('firName', 'Unknown')}",
                        description=alert.get("rawSigmet"),
                        affected_area={
                            "hazard": alert.get("hazard"),
                            "fir_id": alert.get("firId"),
                            "fir_name": alert.get("firName"),
                            "series_id": alert.get("seriesId"),
                            "base": alert.get("base"),
                            "top": alert.get("top"),
                        },
                        is_active=True,
                        is_cancelled=False,
                        source="AviationWeather.gov",
                    )

                    session.add(alert_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(
                        f"Error storing weather alert {alert.get('hazard')}: {e}"
                    )
                    continue

            session.commit()
            self.logger.info(
                f"💾 Stored {stored_count} new weather alert records in API table"
            )
            return stored_count

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error storing weather alert data: {e}")
            return 0
        finally:
            session.close()

    def get_weather_summary(self) -> Dict[str, int]:
        """Get summary of stored weather data"""
        session = SessionLocal()
        try:
            summary = {
                "metars": session.query(METARDataAPI).count(),
                "tafs": session.query(TAFDataAPI).count(),
                "pireps": session.query(PIREPDataAPI).count(),
                "weather_alerts": session.query(WeatherAlertAPI).count(),
                "weather_observations": session.query(WeatherObservationAPI).count(),
                "weather_stations": session.query(WeatherStationAPI).count(),
            }
            return summary
        except Exception as e:
            self.logger.error(f"Error getting weather summary: {e}")
            return {}
        finally:
            session.close()

    def _parse_datetime(self, timestamp: Any) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp:
            return None

        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # ISO format or other string format
                if "T" in timestamp:
                    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing datetime {timestamp}: {e}")
            return None

    def _parse_sky_conditions(self, sky_data: List[Dict]) -> List[Dict]:
        """Parse sky conditions from API data"""
        if not sky_data:
            return []

        conditions = []
        for sky in sky_data:
            if isinstance(sky, dict):
                conditions.append(
                    {
                        "cover": sky.get("cover"),
                        "base": sky.get("base"),
                        "top": sky.get("top"),
                    }
                )
        return conditions

    def _parse_weather_phenomena(self, wx_data: List[str]) -> List[Dict]:
        """Parse weather phenomena from API data"""
        if not wx_data:
            return []

        phenomena = []
        for wx in wx_data:
            if isinstance(wx, str):
                phenomena.append(
                    {"code": wx, "description": self._get_wx_description(wx)}
                )
        return phenomena

    def _parse_forecast_periods(self, forecast_data: List[Dict]) -> List[Dict]:
        """Parse TAF forecast periods"""
        if not forecast_data:
            return []

        periods = []
        for period in forecast_data:
            if isinstance(period, dict):
                periods.append(
                    {
                        "valid_from": self._parse_datetime(period.get("validTimeFrom")),
                        "valid_to": self._parse_datetime(period.get("validTimeTo")),
                        "wind_direction": period.get("wdir"),
                        "wind_speed": period.get("wspd"),
                        "visibility": period.get("visib"),
                        "sky_conditions": self._parse_sky_conditions(
                            period.get("skyc1", [])
                        ),
                        "weather_phenomena": self._parse_weather_phenomena(
                            period.get("wxcodes", [])
                        ),
                    }
                )
        return periods

    def _get_wx_description(self, code: str) -> str:
        """Get description for weather code"""
        wx_descriptions = {
            "TS": "Thunderstorm",
            "RA": "Rain",
            "SN": "Snow",
            "FG": "Fog",
            "BR": "Mist",
            "HZ": "Haze",
            "DU": "Dust",
            "SA": "Sand",
            "FU": "Smoke",
            "VA": "Volcanic Ash",
            "SQ": "Squall",
            "FC": "Funnel Cloud",
            "SS": "Sandstorm",
            "DS": "Duststorm",
        }
        return wx_descriptions.get(code, code)
