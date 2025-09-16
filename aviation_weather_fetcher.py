#!/usr/bin/env python3
"""
AviationWeather.gov API Data Fetcher

This service fetches weather data from the AviationWeather.gov API and stores it
in our database for historical tracking and flight detail integration.

API Documentation: https://aviationweather.gov/data/schema/openapi.yaml
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from db_config import SessionLocal
from models.sqlalchemy.weather_api import (
    WeatherStationAPI,
    METARDataAPI,
    TAFDataAPI,
    WeatherAlertAPI,
)
from storers.weather_api_storer import WeatherAPIStorer
from utils.logger import logger


class AviationWeatherFetcher:
    """Fetches weather data from AviationWeather.gov API"""

    BASE_URL = "https://aviationweather.gov/api/data"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "GolfMike-FlightTracker/1.0 (Weather Data Integration)",
                "Accept": "application/json",
            }
        )
        self.logger = logger
        self.storer = WeatherAPIStorer()

    def fetch_metars(
        self, station_ids: List[str] = None, bbox: str = None, hours: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch METAR data from AviationWeather.gov API

        Args:
            station_ids: List of ICAO station IDs (e.g., ['KLAX', 'KJFK'])
            bbox: Bounding box as "west,south,east,north" (e.g., "-118.5,33.5,-118.0,34.0")
            hours: Hours back to fetch data (default: 1)

        Returns:
            List of METAR data dictionaries
        """
        try:
            params = {"hours": hours, "format": "json"}

            if station_ids:
                params["ids"] = ",".join(station_ids)
            elif bbox:
                params["bbox"] = bbox
            else:
                # Default to major US airports if no specific request
                params["ids"] = "KLAX,KJFK,KORD,KDFW,KATL,KSEA,KDEN,KIAH,KLAS,KMIA"

            response = self.session.get(
                f"{self.BASE_URL}/metar", params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(
                f"✅ Fetched {len(data)} METAR records from AviationWeather.gov"
            )
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error fetching METAR data: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error parsing METAR JSON: {e}")
            return []

    def fetch_tafs(
        self, station_ids: List[str] = None, bbox: str = None, hours: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Fetch TAF data from AviationWeather.gov API

        Args:
            station_ids: List of ICAO station IDs
            bbox: Bounding box as "west,south,east,north"
            hours: Hours back to fetch data (default: 6)

        Returns:
            List of TAF data dictionaries
        """
        try:
            params = {"hours": hours, "format": "json"}

            if station_ids:
                params["ids"] = ",".join(station_ids)
            elif bbox:
                params["bbox"] = bbox
            else:
                # Default to major US airports
                params["ids"] = "KLAX,KJFK,KORD,KDFW,KATL,KSEA,KDEN,KIAH,KLAS,KMIA"

            response = self.session.get(
                f"{self.BASE_URL}/taf", params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(
                f"✅ Fetched {len(data)} TAF records from AviationWeather.gov"
            )
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error fetching TAF data: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error parsing TAF JSON: {e}")
            return []

    def fetch_pireps(self, bbox: str = None, hours: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch PIREP data from AviationWeather.gov API

        Args:
            bbox: Bounding box as "west,south,east,north"
            hours: Hours back to fetch data (default: 2)

        Returns:
            List of PIREP data dictionaries
        """
        try:
            params = {"hours": hours, "format": "json"}

            if bbox:
                params["bbox"] = bbox
            else:
                # Default to continental US
                params["bbox"] = "-125.0,25.0,-66.0,49.0"

            response = self.session.get(
                f"{self.BASE_URL}/pirep", params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(
                f"✅ Fetched {len(data)} PIREP records from AviationWeather.gov"
            )
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error fetching PIREP data: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error parsing PIREP JSON: {e}")
            return []

    def fetch_airsigmets(self, hours: int = 6) -> List[Dict[str, Any]]:
        """
        Fetch AIRMET/SIGMET data from AviationWeather.gov API

        Args:
            hours: Hours back to fetch data (default: 6)

        Returns:
            List of AIRMET/SIGMET data dictionaries
        """
        try:
            params = {"hours": hours, "format": "json"}

            response = self.session.get(
                f"{self.BASE_URL}/airsigmet", params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(
                f"✅ Fetched {len(data)} AIRMET/SIGMET records from AviationWeather.gov"
            )
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error fetching AIRMET/SIGMET data: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Error parsing AIRMET/SIGMET JSON: {e}")
            return []

    def store_metar_data(self, metar_data: List[Dict[str, Any]]) -> int:
        """Store METAR data in database"""
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
                    )

                    session.add(metar_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Error storing METAR {metar.get('icaoId')}: {e}")
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new METAR records")
            return stored_count

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing METAR data: {e}")
            return 0
        finally:
            session.close()

    def store_taf_data(self, taf_data: List[Dict[str, Any]]) -> int:
        """Store TAF data in database"""
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
                    )

                    session.add(taf_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(f"Error storing TAF {taf.get('icaoId')}: {e}")
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new TAF records")
            return stored_count

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing TAF data: {e}")
            return 0
        finally:
            session.close()

    def store_airsigmet_data(self, airsigmet_data: List[Dict[str, Any]]) -> int:
        """Store AIRMET/SIGMET data in database"""
        stored_count = 0
        session = SessionLocal()

        try:
            for alert in airsigmet_data:
                try:
                    # Create unique alert ID
                    alert_id = f"AWS_{alert.get('hazard', 'UNKNOWN')}_{alert.get('validTimeFrom', 'UNKNOWN')}"

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
                    )

                    session.add(alert_record)
                    stored_count += 1

                except Exception as e:
                    self.logger.error(
                        f"Error storing AIRMET/SIGMET {alert.get('hazard')}: {e}"
                    )
                    continue

            session.commit()
            self.logger.info(f"💾 Stored {stored_count} new AIRMET/SIGMET records")
            return stored_count

        except Exception as e:
            session.rollback()
            self.logger.error(f"Error storing AIRMET/SIGMET data: {e}")
            return 0
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

    def fetch_and_store_all(
        self, station_ids: List[str] = None, bbox: str = None
    ) -> Dict[str, int]:
        """Fetch and store all weather data types"""
        results = {}

        self.logger.info("🌤️  Starting AviationWeather.gov data fetch...")

        # Fetch METARs
        metar_data = self.fetch_metars(station_ids, bbox)
        if metar_data:
            results["metars"] = self.storer.store_metar_data(metar_data)

        # Fetch TAFs
        taf_data = self.fetch_tafs(station_ids, bbox)
        if taf_data:
            results["tafs"] = self.storer.store_taf_data(taf_data)

        # Fetch PIREPs
        pirep_data = self.fetch_pireps(bbox)
        if pirep_data:
            results["pireps"] = self.storer.store_pirep_data(pirep_data)

        # Fetch AIRMETs/SIGMETs
        airsigmet_data = self.fetch_airsigmets()
        if airsigmet_data:
            results["airsigmets"] = self.storer.store_weather_alert_data(airsigmet_data)

        self.logger.info(f"✅ AviationWeather.gov fetch complete: {results}")
        return results


def run_weather_fetch():
    """Main function to run weather data fetch"""
    fetcher = AviationWeatherFetcher()

    # Fetch data for major US airports
    major_airports = [
        "KLAX",
        "KJFK",
        "KORD",
        "KDFW",
        "KATL",
        "KSEA",
        "KDEN",
        "KIAH",
        "KLAS",
        "KMIA",
        "KBOS",
        "KPHX",
        "KMSP",
        "KDTW",
        "KPHL",
        "KCLT",
        "KMCO",
        "KTPA",
        "KPDX",
        "KSLC",
    ]

    results = fetcher.fetch_and_store_all(station_ids=major_airports)

    # Log summary
    total_records = sum(results.values())
    logger.info(f"🌤️  Weather data fetch complete: {total_records} total records stored")

    return results


if __name__ == "__main__":
    run_weather_fetch()
