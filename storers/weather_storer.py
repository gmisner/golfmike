"""
Weather Data Storer
Stores parsed weather data (METAR, TAF, NOTAMs, etc.) to the database
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.exc import SQLAlchemyError
from db_config import SessionLocal
from models.sqlalchemy.weather import (
    WeatherStation,
    METARData,
    TAFData,
    NOTAMData,
    WeatherAlert,
    WeatherObservation,
)
from models.pydantic.weather import (
    METARModel,
    TAFModel,
    NOTAMModel,
    WeatherAlertModel,
    WeatherObservationModel,
    WeatherStationModel,
)
from utils.logger import main_logger as logger


class WeatherDataStorer:
    """Stores weather data to the database"""

    def __init__(self):
        self.logger = logger

    def store_weather_data(self, weather_data: Dict[str, Any]) -> bool:
        """
        Store weather data based on its type

        Args:
            weather_data: Dictionary containing weather data and type

        Returns:
            Boolean indicating success
        """
        try:
            data_type = weather_data.get("type")
            data = weather_data.get("data", {})

            if data_type == "METAR":
                return self._store_metar(data)
            elif data_type == "TAF":
                return self._store_taf(data)
            elif data_type == "NOTAM":
                return self._store_notam(data)
            elif data_type == "SIGMET":
                return self._store_sigmet(data)
            elif data_type == "AIRMET":
                return self._store_airmet(data)
            elif data_type in [
                "ITWS_ALERT",
                "ITWS_LIGHTNING",
                "ITWS_PRECIPITATION",
                "ITWS_MICROBURST",
                "ITWS_TORNADO",
                "ITWS_GUST_FRONT",
                "ITWS_GENERIC",
            ]:
                return self._store_itws_msg(data, data_type)
            elif data_type == "ITWS":
                return self._store_itws(data)
            else:
                self.logger.warning(f"Unknown weather data type: {data_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error storing weather data: {e}")
            return False

    def _store_metar(self, metar_data: Dict[str, Any]) -> bool:
        """Store METAR data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not metar_data.get("station_id") or not metar_data.get(
                "observation_time"
            ):
                self.logger.error(
                    "Missing required METAR fields: station_id or observation_time"
                )
                return False

            # Check if METAR already exists
            existing_metar = (
                session.query(METARData)
                .filter(
                    METARData.station_id == metar_data["station_id"],
                    METARData.observation_time == metar_data["observation_time"],
                )
                .first()
            )

            if existing_metar:
                self.logger.info(
                    f"METAR already exists for {metar_data['station_id']} at {metar_data['observation_time']}"
                )
                return True

            # Create new METAR record
            metar_record = METARData(
                station_id=metar_data["station_id"],
                observation_time=metar_data["observation_time"],
                raw_text=metar_data.get("raw_text"),
                wind_direction=metar_data.get("wind_direction"),
                wind_speed=metar_data.get("wind_speed"),
                wind_gust=metar_data.get("wind_gust"),
                visibility=metar_data.get("visibility"),
                visibility_units=metar_data.get("visibility_units"),
                sky_conditions=metar_data.get("sky_conditions"),
                temperature=metar_data.get("temperature"),
                dewpoint=metar_data.get("dewpoint"),
                altimeter=metar_data.get("altimeter"),
                weather_phenomena=metar_data.get("weather_phenomena"),
                flight_category=metar_data.get("flight_category"),
                sea_level_pressure=metar_data.get("sea_level_pressure"),
                pressure_tendency=metar_data.get("pressure_tendency"),
            )

            session.add(metar_record)
            session.commit()

            self.logger.info(
                f"✅ Stored METAR for {metar_data['station_id']} at {metar_data['observation_time']}"
            )
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing METAR: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing METAR: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_taf(self, taf_data: Dict[str, Any]) -> bool:
        """Store TAF data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not taf_data.get("station_id") or not taf_data.get("issue_time"):
                self.logger.error(
                    "Missing required TAF fields: station_id or issue_time"
                )
                return False

            # Check if TAF already exists
            existing_taf = (
                session.query(TAFData)
                .filter(
                    TAFData.station_id == taf_data["station_id"],
                    TAFData.issue_time == taf_data["issue_time"],
                )
                .first()
            )

            if existing_taf:
                self.logger.info(
                    f"TAF already exists for {taf_data['station_id']} at {taf_data['issue_time']}"
                )
                return True

            # Create new TAF record
            taf_record = TAFData(
                station_id=taf_data["station_id"],
                issue_time=taf_data["issue_time"],
                valid_from=taf_data.get("valid_from"),
                valid_to=taf_data.get("valid_to"),
                raw_text=taf_data.get("raw_text"),
                forecast_periods=taf_data.get("forecast_periods"),
                wind_direction=taf_data.get("wind_direction"),
                wind_speed=taf_data.get("wind_speed"),
                wind_gust=taf_data.get("wind_gust"),
                visibility=taf_data.get("visibility"),
                visibility_units=taf_data.get("visibility_units"),
                sky_conditions=taf_data.get("sky_conditions"),
                weather_phenomena=taf_data.get("weather_phenomena"),
                flight_category=taf_data.get("flight_category"),
                probability=taf_data.get("probability"),
            )

            session.add(taf_record)
            session.commit()

            self.logger.info(
                f"✅ Stored TAF for {taf_data['station_id']} at {taf_data['issue_time']}"
            )
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing TAF: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing TAF: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_notam(self, notam_data: Dict[str, Any]) -> bool:
        """Store NOTAM data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not notam_data.get("notam_id") or not notam_data.get("effective_from"):
                self.logger.error(
                    "Missing required NOTAM fields: notam_id or effective_from"
                )
                return False

            # Check if NOTAM already exists
            existing_notam = (
                session.query(NOTAMData)
                .filter(NOTAMData.notam_id == notam_data["notam_id"])
                .first()
            )

            if existing_notam:
                # Update existing NOTAM
                existing_notam.notam_number = notam_data.get("notam_number")
                existing_notam.location_identifier = notam_data.get(
                    "location_identifier"
                )
                existing_notam.location_type = notam_data.get("location_type")
                existing_notam.effective_from = notam_data.get("effective_from")
                existing_notam.effective_until = notam_data.get("effective_until")
                existing_notam.raw_text = notam_data.get("raw_text")
                existing_notam.summary = notam_data.get("summary")
                existing_notam.description = notam_data.get("description")
                existing_notam.notam_type = notam_data.get("notam_type")
                existing_notam.priority = notam_data.get("priority")
                existing_notam.category = notam_data.get("category")
                existing_notam.is_active = notam_data.get("is_active", True)
                existing_notam.is_cancelled = notam_data.get("is_cancelled", False)
                existing_notam.altitude_floor = notam_data.get("altitude_floor")
                existing_notam.altitude_ceiling = notam_data.get("altitude_ceiling")
                existing_notam.coordinates = notam_data.get("coordinates")

                self.logger.info(f"✅ Updated NOTAM {notam_data['notam_id']}")
            else:
                # Create new NOTAM record
                notam_record = NOTAMData(
                    notam_id=notam_data["notam_id"],
                    notam_number=notam_data.get("notam_number"),
                    location_identifier=notam_data.get("location_identifier"),
                    location_type=notam_data.get("location_type"),
                    effective_from=notam_data.get("effective_from"),
                    effective_until=notam_data.get("effective_until"),
                    raw_text=notam_data.get("raw_text"),
                    summary=notam_data.get("summary"),
                    description=notam_data.get("description"),
                    notam_type=notam_data.get("notam_type"),
                    priority=notam_data.get("priority"),
                    category=notam_data.get("category"),
                    is_active=notam_data.get("is_active", True),
                    is_cancelled=notam_data.get("is_cancelled", False),
                    altitude_floor=notam_data.get("altitude_floor"),
                    altitude_ceiling=notam_data.get("altitude_ceiling"),
                    coordinates=notam_data.get("coordinates"),
                )

                session.add(notam_record)
                self.logger.info(f"✅ Stored new NOTAM {notam_data['notam_id']}")

            session.commit()
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing NOTAM: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing NOTAM: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_sigmet(self, sigmet_data: Dict[str, Any]) -> bool:
        """Store SIGMET data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not sigmet_data.get("alert_id") or not sigmet_data.get("valid_from"):
                self.logger.error(
                    "Missing required SIGMET fields: alert_id or valid_from"
                )
                return False

            # Check if SIGMET already exists
            existing_sigmet = (
                session.query(WeatherAlert)
                .filter(WeatherAlert.alert_id == sigmet_data["alert_id"])
                .first()
            )

            if existing_sigmet:
                # Update existing SIGMET
                existing_sigmet.alert_type = sigmet_data.get("alert_type", "SIGMET")
                existing_sigmet.severity = sigmet_data.get("severity")
                existing_sigmet.urgency = sigmet_data.get("urgency")
                existing_sigmet.valid_from = sigmet_data.get("valid_from")
                existing_sigmet.valid_until = sigmet_data.get("valid_until")
                existing_sigmet.issued_at = sigmet_data.get("issued_at")
                existing_sigmet.raw_text = sigmet_data.get("raw_text")
                existing_sigmet.summary = sigmet_data.get("summary")
                existing_sigmet.description = sigmet_data.get("description")
                existing_sigmet.weather_phenomena = sigmet_data.get("weather_phenomena")
                existing_sigmet.altitude_floor = sigmet_data.get("altitude_floor")
                existing_sigmet.altitude_ceiling = sigmet_data.get("altitude_ceiling")
                existing_sigmet.affected_area = sigmet_data.get("affected_area")
                existing_sigmet.affected_airports = sigmet_data.get("affected_airports")
                existing_sigmet.is_active = sigmet_data.get("is_active", True)
                existing_sigmet.is_cancelled = sigmet_data.get("is_cancelled", False)

                self.logger.info(f"✅ Updated SIGMET {sigmet_data['alert_id']}")
            else:
                # Create new SIGMET record
                sigmet_record = WeatherAlert(
                    alert_id=sigmet_data["alert_id"],
                    alert_type=sigmet_data.get("alert_type", "SIGMET"),
                    severity=sigmet_data.get("severity"),
                    urgency=sigmet_data.get("urgency"),
                    valid_from=sigmet_data.get("valid_from"),
                    valid_until=sigmet_data.get("valid_until"),
                    issued_at=sigmet_data.get("issued_at"),
                    raw_text=sigmet_data.get("raw_text"),
                    summary=sigmet_data.get("summary"),
                    description=sigmet_data.get("description"),
                    weather_phenomena=sigmet_data.get("weather_phenomena"),
                    altitude_floor=sigmet_data.get("altitude_floor"),
                    altitude_ceiling=sigmet_data.get("altitude_ceiling"),
                    affected_area=sigmet_data.get("affected_area"),
                    affected_airports=sigmet_data.get("affected_airports"),
                    is_active=sigmet_data.get("is_active", True),
                    is_cancelled=sigmet_data.get("is_cancelled", False),
                )

                session.add(sigmet_record)
                self.logger.info(f"✅ Stored new SIGMET {sigmet_data['alert_id']}")

            session.commit()
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing SIGMET: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing SIGMET: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_airmet(self, airmet_data: Dict[str, Any]) -> bool:
        """Store AIRMET data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not airmet_data.get("alert_id") or not airmet_data.get("valid_from"):
                self.logger.error(
                    "Missing required AIRMET fields: alert_id or valid_from"
                )
                return False

            # Check if AIRMET already exists
            existing_airmet = (
                session.query(WeatherAlert)
                .filter(WeatherAlert.alert_id == airmet_data["alert_id"])
                .first()
            )

            if existing_airmet:
                # Update existing AIRMET
                existing_airmet.alert_type = airmet_data.get("alert_type", "AIRMET")
                existing_airmet.severity = airmet_data.get("severity")
                existing_airmet.urgency = airmet_data.get("urgency")
                existing_airmet.valid_from = airmet_data.get("valid_from")
                existing_airmet.valid_until = airmet_data.get("valid_until")
                existing_airmet.issued_at = airmet_data.get("issued_at")
                existing_airmet.raw_text = airmet_data.get("raw_text")
                existing_airmet.summary = airmet_data.get("summary")
                existing_airmet.description = airmet_data.get("description")
                existing_airmet.weather_phenomena = airmet_data.get("weather_phenomena")
                existing_airmet.altitude_floor = airmet_data.get("altitude_floor")
                existing_airmet.altitude_ceiling = airmet_data.get("altitude_ceiling")
                existing_airmet.affected_area = airmet_data.get("affected_area")
                existing_airmet.affected_airports = airmet_data.get("affected_airports")
                existing_airmet.is_active = airmet_data.get("is_active", True)
                existing_airmet.is_cancelled = airmet_data.get("is_cancelled", False)

                self.logger.info(f"✅ Updated AIRMET {airmet_data['alert_id']}")
            else:
                # Create new AIRMET record
                airmet_record = WeatherAlert(
                    alert_id=airmet_data["alert_id"],
                    alert_type=airmet_data.get("alert_type", "AIRMET"),
                    severity=airmet_data.get("severity"),
                    urgency=airmet_data.get("urgency"),
                    valid_from=airmet_data.get("valid_from"),
                    valid_until=airmet_data.get("valid_until"),
                    issued_at=airmet_data.get("issued_at"),
                    raw_text=airmet_data.get("raw_text"),
                    summary=airmet_data.get("summary"),
                    description=airmet_data.get("description"),
                    weather_phenomena=airmet_data.get("weather_phenomena"),
                    altitude_floor=airmet_data.get("altitude_floor"),
                    altitude_ceiling=airmet_data.get("altitude_ceiling"),
                    affected_area=airmet_data.get("affected_area"),
                    affected_airports=airmet_data.get("affected_airports"),
                    is_active=airmet_data.get("is_active", True),
                    is_cancelled=airmet_data.get("is_cancelled", False),
                )

                session.add(airmet_record)
                self.logger.info(f"✅ Stored new AIRMET {airmet_data['alert_id']}")

            session.commit()
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing AIRMET: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing AIRMET: {e}")
            return False
        finally:
            if session:
                session.close()

    def get_weather_summary(self) -> Dict[str, int]:
        """Get summary of weather data in database"""
        try:
            session = SessionLocal()

            summary = {
                "metar_count": session.query(METARData).count(),
                "taf_count": session.query(TAFData).count(),
                "notam_count": session.query(NOTAMData).count(),
                "weather_alert_count": session.query(WeatherAlert).count(),
                "weather_observation_count": session.query(WeatherObservation).count(),
            }

            session.close()
            return summary

        except Exception as e:
            self.logger.error(f"Error getting weather summary: {e}")
            return {}

    def _store_itws_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store ITWS Alert data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not alert_data.get("alert_id") or not alert_data.get("valid_from"):
                self.logger.error(
                    "Missing required ITWS Alert fields: alert_id or valid_from"
                )
                return False

            # Check if ITWS Alert already exists
            existing_alert = (
                session.query(WeatherAlert)
                .filter(WeatherAlert.alert_id == alert_data["alert_id"])
                .first()
            )

            if existing_alert:
                # Update existing ITWS Alert
                existing_alert.alert_type = alert_data.get("alert_type", "ITWS_ALERT")
                existing_alert.severity = alert_data.get("severity")
                existing_alert.urgency = alert_data.get("urgency")
                existing_alert.valid_from = alert_data.get("valid_from")
                existing_alert.valid_until = alert_data.get("valid_until")
                existing_alert.issued_at = alert_data.get("issued_at")
                existing_alert.raw_text = alert_data.get("raw_text")
                existing_alert.summary = alert_data.get("summary")
                existing_alert.description = alert_data.get("description")
                existing_alert.weather_phenomena = alert_data.get("weather_phenomena")
                existing_alert.altitude_floor = alert_data.get("altitude_floor")
                existing_alert.altitude_ceiling = alert_data.get("altitude_ceiling")
                existing_alert.affected_area = alert_data.get("affected_area")
                existing_alert.affected_airports = alert_data.get("affected_airports")
                existing_alert.is_active = alert_data.get("is_active", True)
                existing_alert.is_cancelled = alert_data.get("is_cancelled", False)

                self.logger.info(f"✅ Updated ITWS Alert {alert_data['alert_id']}")
            else:
                # Create new ITWS Alert record
                alert_record = WeatherAlert(
                    alert_id=alert_data["alert_id"],
                    alert_type=alert_data.get("alert_type", "ITWS_ALERT"),
                    severity=alert_data.get("severity"),
                    urgency=alert_data.get("urgency"),
                    valid_from=alert_data.get("valid_from"),
                    valid_until=alert_data.get("valid_until"),
                    issued_at=alert_data.get("issued_at"),
                    raw_text=alert_data.get("raw_text"),
                    summary=alert_data.get("summary"),
                    description=alert_data.get("description"),
                    weather_phenomena=alert_data.get("weather_phenomena"),
                    altitude_floor=alert_data.get("altitude_floor"),
                    altitude_ceiling=alert_data.get("altitude_ceiling"),
                    affected_area=alert_data.get("affected_area"),
                    affected_airports=alert_data.get("affected_airports"),
                    is_active=alert_data.get("is_active", True),
                    is_cancelled=alert_data.get("is_cancelled", False),
                )

                session.add(alert_record)
                self.logger.info(f"✅ Stored new ITWS Alert {alert_data['alert_id']}")

            session.commit()
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing ITWS Alert: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing ITWS Alert: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_itws(self, itws_data: Dict[str, Any]) -> bool:
        """Store ITWS data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not itws_data.get("message_id") or not itws_data.get("timestamp"):
                self.logger.error(
                    "Missing required ITWS fields: message_id or timestamp"
                )
                return False

            # Check if ITWS message already exists
            existing_itws = (
                session.query(WeatherObservation)
                .filter(
                    WeatherObservation.station_id
                    == itws_data.get("airport_id", "UNKNOWN"),
                    WeatherObservation.observation_time == itws_data.get("timestamp"),
                )
                .first()
            )

            if existing_itws:
                self.logger.info(
                    f"ITWS message already exists for {itws_data.get('airport_id')} at {itws_data.get('timestamp')}"
                )
                return True

            # Create new ITWS observation record
            itws_record = WeatherObservation(
                station_id=itws_data.get("airport_id", "UNKNOWN"),
                observation_time=itws_data.get("timestamp"),
                temperature=itws_data.get("temperature"),
                dewpoint=itws_data.get("dewpoint"),
                wind_direction=itws_data.get("wind_direction"),
                wind_speed=itws_data.get("wind_speed"),
                wind_gust=itws_data.get("wind_gust"),
                visibility=itws_data.get("visibility"),
                raw_data={
                    "message_id": itws_data.get("message_id"),
                    "center_id": itws_data.get("center_id"),
                    "message_type": itws_data.get("message_type"),
                    "sky_conditions": itws_data.get("sky_conditions"),
                    "weather_phenomena": itws_data.get("weather_phenomena"),
                    "flight_category": itws_data.get("flight_category"),
                    "raw_text": itws_data.get("raw_text"),
                    "summary": itws_data.get("summary"),
                    "description": itws_data.get("description"),
                },
                data_source="ITWS",
            )

            session.add(itws_record)
            session.commit()

            self.logger.info(
                f"✅ Stored ITWS data for {itws_data.get('airport_id')} at {itws_data.get('timestamp')}"
            )
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing ITWS: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing ITWS: {e}")
            return False
        finally:
            if session:
                session.close()

    def _store_itws_msg(self, itws_data: Dict[str, Any], data_type: str) -> bool:
        """Store ITWS message data to database"""
        session = None
        try:
            session = SessionLocal()

            # Validate required fields
            if not itws_data.get("alert_id") or not itws_data.get("generation_time"):
                self.logger.error(
                    "Missing required ITWS message fields: alert_id or generation_time"
                )
                return False

            # Check if ITWS message already exists
            existing_alert = (
                session.query(WeatherAlert)
                .filter(WeatherAlert.alert_id == itws_data["alert_id"])
                .first()
            )

            if existing_alert:
                # Update existing ITWS message
                existing_alert.alert_type = data_type
                existing_alert.valid_from = itws_data.get("generation_time")
                existing_alert.valid_until = itws_data.get("expiration_time")
                # Use generation_time as fallback if received_time is None
                existing_alert.issued_at = itws_data.get(
                    "received_time"
                ) or itws_data.get("generation_time")
                existing_alert.raw_text = (
                    f"ITWS {data_type}: {itws_data.get('product_msg_name', 'Unknown')}"
                )
                existing_alert.summary = f"{data_type} alert for {itws_data.get('airports', 'Unknown')} from {itws_data.get('itws_sites', 'Unknown')}"
                existing_alert.description = f"Product: {itws_data.get('product_msg_name', 'Unknown')}, Type: {itws_data.get('product_type', 'Unknown')}"

                # Store additional data in affected_area JSON field
                affected_area = {
                    "itws_sites": itws_data.get("itws_sites"),
                    "airports": itws_data.get("airports"),
                    "source_id": itws_data.get("source_id"),
                    "product_type": itws_data.get("product_type"),
                    "packet_msgno": itws_data.get("packet_msgno"),
                    "packet_size": itws_data.get("packet_size"),
                }

                # Add type-specific data
                if data_type == "ITWS_PRECIPITATION":
                    affected_area.update(
                        {
                            "latitude": itws_data.get("latitude"),
                            "longitude": itws_data.get("longitude"),
                            "grid_size": f"{itws_data.get('nrows', 0)}x{itws_data.get('ncols', 0)}",
                            "volume_scan_num": itws_data.get("volume_scan_num"),
                        }
                    )
                elif data_type == "ITWS_LIGHTNING":
                    affected_area["lightning_enc"] = itws_data.get("lightning_enc")

                existing_alert.affected_area = affected_area
                existing_alert.affected_airports = (
                    [itws_data.get("airports")] if itws_data.get("airports") else None
                )

                self.logger.info(f"✅ Updated ITWS {data_type} {itws_data['alert_id']}")
            else:
                # Create new ITWS message record
                alert_record = WeatherAlert(
                    alert_id=itws_data["alert_id"],
                    alert_type=data_type,
                    severity="MODERATE",  # Default severity for ITWS alerts
                    urgency="EXPECTED",  # Default urgency for ITWS alerts
                    valid_from=itws_data.get("generation_time"),
                    valid_until=itws_data.get("expiration_time"),
                    issued_at=itws_data.get("received_time")
                    or itws_data.get("generation_time"),
                    raw_text=f"ITWS {data_type}: {itws_data.get('product_msg_name', 'Unknown')}",
                    summary=f"{data_type} alert for {itws_data.get('airports', 'Unknown')} from {itws_data.get('itws_sites', 'Unknown')}",
                    description=f"Product: {itws_data.get('product_msg_name', 'Unknown')}, Type: {itws_data.get('product_type', 'Unknown')}",
                    is_active=True,
                    is_cancelled=False,
                )

                # Store additional data in affected_area JSON field
                affected_area = {
                    "itws_sites": itws_data.get("itws_sites"),
                    "airports": itws_data.get("airports"),
                    "source_id": itws_data.get("source_id"),
                    "product_type": itws_data.get("product_type"),
                    "packet_msgno": itws_data.get("packet_msgno"),
                    "packet_size": itws_data.get("packet_size"),
                }

                # Add type-specific data
                if data_type == "ITWS_PRECIPITATION":
                    affected_area.update(
                        {
                            "latitude": itws_data.get("latitude"),
                            "longitude": itws_data.get("longitude"),
                            "grid_size": f"{itws_data.get('nrows', 0)}x{itws_data.get('ncols', 0)}",
                            "volume_scan_num": itws_data.get("volume_scan_num"),
                        }
                    )
                elif data_type == "ITWS_LIGHTNING":
                    affected_area["lightning_enc"] = itws_data.get("lightning_enc")

                alert_record.affected_area = affected_area
                alert_record.affected_airports = (
                    [itws_data.get("airports")] if itws_data.get("airports") else None
                )

                session.add(alert_record)
                self.logger.info(
                    f"✅ Stored new ITWS {data_type} {itws_data['alert_id']}"
                )

            session.commit()
            return True

        except SQLAlchemyError as e:
            if session:
                session.rollback()
            self.logger.error(f"Database error storing ITWS {data_type}: {e}")
            return False
        except Exception as e:
            if session:
                session.rollback()
            self.logger.error(f"Error storing ITWS {data_type}: {e}")
            return False
        finally:
            if session:
                session.close()
