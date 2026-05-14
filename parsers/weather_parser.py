"""
Weather Data XML Parser
Parses METAR, TAF, NOTAMs, and other weather data from FAA SWIM XML messages
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from lxml import etree, objectify
from models.pydantic.weather import (
    METARModel,
    TAFModel,
    NOTAMModel,
    WeatherAlertModel,
    WeatherObservationModel,
    WeatherPhenomenon,
    SkyCondition,
    FlightCategory,
    WeatherStationModel,
)
from utils.logger import main_logger as logger


class WeatherXMLParser:
    """Parser for weather-related XML messages from FAA SWIM"""

    def __init__(self):
        self.logger = logger

    def parse_message(
        self, xml_content: str, message_type: str = None
    ) -> Dict[str, Any]:
        """
        Parse weather XML message and return structured data

        Args:
            xml_content: Raw XML content
            message_type: Type of message (METAR, TAF, NOTAM, etc.)

        Returns:
            Dictionary containing parsed weather data
        """
        try:
            # Parse XML
            root = etree.fromstring(xml_content.encode("utf-8"))

            # Determine message type if not provided
            if not message_type:
                message_type = self._detect_message_type(root)

            # Parse based on message type
            if message_type == "METAR":
                return self._parse_metar(root)
            elif message_type == "TAF":
                return self._parse_taf(root)
            elif message_type == "NOTAM":
                return self._parse_notam(root)
            elif message_type == "SIGMET":
                return self._parse_sigmet(root)
            elif message_type == "AIRMET":
                return self._parse_airmet(root)
            elif message_type in [
                "ITWS_ALERT",
                "ITWS_LIGHTNING",
                "ITWS_PRECIPITATION",
                "ITWS_MICROBURST",
                "ITWS_TORNADO",
                "ITWS_GUST_FRONT",
                "ITWS_GENERIC",
            ]:
                return self._parse_itws_msg(root, message_type)
            elif message_type == "ITWS":
                return self._parse_itws(root)
            else:
                return self._parse_generic_weather(root)

        except Exception as e:
            self.logger.error(f"Error parsing weather XML: {e}")
            return {"error": str(e), "raw_content": xml_content}

    def parse_weather_xml(
        self, xml_content: str, message_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Backward-compatible alias for :meth:`parse_message`."""
        return self.parse_message(xml_content, message_type)

    def _detect_message_type(self, root: etree.Element) -> str:
        """Detect the type of weather message from XML structure"""
        # Check for common weather message indicators
        if root.tag.endswith("METAR") or "METAR" in root.tag:
            return "METAR"
        elif root.tag.endswith("TAF") or "TAF" in root.tag:
            return "TAF"
        elif root.tag.endswith("NOTAM") or "NOTAM" in root.tag:
            return "NOTAM"
        elif root.tag.endswith("SIGMET") or "SIGMET" in root.tag:
            return "SIGMET"
        elif root.tag.endswith("AIRMET") or "AIRMET" in root.tag:
            return "AIRMET"
        elif root.tag == "itws_msg":
            # Check the product name to determine specific type
            product_name = self._get_text(root, ".//product_msg_name")
            if product_name:
                if "Lightning" in product_name:
                    return "ITWS_LIGHTNING"
                elif "Precipitation" in product_name:
                    return "ITWS_PRECIPITATION"
                elif "Microburst" in product_name:
                    return "ITWS_MICROBURST"
                elif "Tornado" in product_name:
                    return "ITWS_TORNADO"
                elif "Gust Front" in product_name:
                    return "ITWS_GUST_FRONT"
                elif "Alert" in product_name:
                    return "ITWS_ALERT"
                else:
                    return "ITWS_GENERIC"
            else:
                return "ITWS_GENERIC"
        elif root.tag.endswith("ITWS_Alert") or "ITWS_Alert" in root.tag:
            return "ITWS_ALERT"
        elif root.tag.endswith("ITWS") or "ITWS" in root.tag:
            return "ITWS"
        else:
            return "UNKNOWN"

    def _parse_metar(self, root: etree.Element) -> Dict[str, Any]:
        """Parse METAR XML data"""
        try:
            metar_data = {}

            # Extract basic information
            metar_data["station_id"] = self._get_text(
                root, ".//stationId"
            ) or self._get_text(root, ".//station")
            metar_data["observation_time"] = self._parse_datetime(
                self._get_text(root, ".//observationTime")
                or self._get_text(root, ".//time")
            )
            metar_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")

            # Parse wind data
            wind_elem = root.find(".//wind")
            if wind_elem is not None:
                metar_data["wind_direction"] = self._get_int(wind_elem, ".//direction")
                metar_data["wind_speed"] = self._get_int(wind_elem, ".//speed")
                metar_data["wind_gust"] = self._get_int(wind_elem, ".//gust")

            # Parse visibility
            visibility_elem = root.find(".//visibility")
            if visibility_elem is not None:
                metar_data["visibility"] = self._get_float(visibility_elem, ".//value")
                metar_data["visibility_units"] = self._get_text(
                    visibility_elem, ".//unit"
                )

            # Parse sky conditions
            sky_conditions = []
            for sky_elem in root.findall(".//skyCondition"):
                sky_condition = {
                    "coverage": self._get_text(sky_elem, ".//coverage"),
                    "altitude": self._get_int(sky_elem, ".//altitude"),
                    "cloud_type": self._get_text(sky_elem, ".//cloudType"),
                }
                sky_conditions.append(sky_condition)
            metar_data["sky_conditions"] = sky_conditions

            # Parse temperature and pressure
            temp_elem = root.find(".//temperature")
            if temp_elem is not None:
                metar_data["temperature"] = self._get_float(temp_elem, ".//value")

            dewpoint_elem = root.find(".//dewpoint")
            if dewpoint_elem is not None:
                metar_data["dewpoint"] = self._get_float(dewpoint_elem, ".//value")

            altimeter_elem = root.find(".//altimeter")
            if altimeter_elem is not None:
                metar_data["altimeter"] = self._get_float(altimeter_elem, ".//value")

            # Parse weather phenomena
            weather_phenomena = []
            for weather_elem in root.findall(".//weatherPhenomena"):
                phenomenon = {
                    "code": self._get_text(weather_elem, ".//code"),
                    "intensity": self._get_text(weather_elem, ".//intensity"),
                    "descriptor": self._get_text(weather_elem, ".//descriptor"),
                    "proximity": self._get_text(weather_elem, ".//proximity"),
                }
                weather_phenomena.append(phenomenon)
            metar_data["weather_phenomena"] = weather_phenomena

            # Parse flight category
            flight_category = self._get_text(root, ".//flightCategory")
            if flight_category:
                metar_data["flight_category"] = flight_category

            # Parse additional data
            metar_data["sea_level_pressure"] = self._get_float(
                root, ".//seaLevelPressure"
            )
            metar_data["pressure_tendency"] = self._get_float(
                root, ".//pressureTendency"
            )

            return {"type": "METAR", "data": metar_data}

        except Exception as e:
            self.logger.error(f"Error parsing METAR: {e}")
            return {"type": "METAR", "error": str(e)}

    def _parse_taf(self, root: etree.Element) -> Dict[str, Any]:
        """Parse TAF XML data"""
        try:
            taf_data = {}

            # Extract basic information
            taf_data["station_id"] = self._get_text(
                root, ".//stationId"
            ) or self._get_text(root, ".//station")
            taf_data["issue_time"] = self._parse_datetime(
                self._get_text(root, ".//issueTime") or self._get_text(root, ".//time")
            )
            taf_data["valid_from"] = self._parse_datetime(
                self._get_text(root, ".//validFrom")
                or self._get_text(root, ".//validTime/from")
            )
            taf_data["valid_to"] = self._parse_datetime(
                self._get_text(root, ".//validTo")
                or self._get_text(root, ".//validTime/to")
            )
            taf_data["raw_text"] = self._get_text(root, ".//rawText") or self._get_text(
                root, ".//text"
            )

            # Parse forecast periods
            forecast_periods = []
            for period_elem in root.findall(".//forecastPeriod"):
                period = {
                    "valid_from": self._parse_datetime(
                        self._get_text(period_elem, ".//validFrom")
                    ),
                    "valid_until": self._parse_datetime(
                        self._get_text(period_elem, ".//validUntil")
                    ),
                    "wind_direction": self._get_int(period_elem, ".//wind/direction"),
                    "wind_speed": self._get_int(period_elem, ".//wind/speed"),
                    "wind_gust": self._get_int(period_elem, ".//wind/gust"),
                    "visibility": self._get_float(period_elem, ".//visibility/value"),
                    "visibility_units": self._get_text(
                        period_elem, ".//visibility/unit"
                    ),
                    "flight_category": self._get_text(period_elem, ".//flightCategory"),
                    "probability": self._get_int(period_elem, ".//probability"),
                }

                # Parse sky conditions for this period
                sky_conditions = []
                for sky_elem in period_elem.findall(".//skyCondition"):
                    sky_condition = {
                        "coverage": self._get_text(sky_elem, ".//coverage"),
                        "altitude": self._get_int(sky_elem, ".//altitude"),
                        "cloud_type": self._get_text(sky_elem, ".//cloudType"),
                    }
                    sky_conditions.append(sky_condition)
                period["sky_conditions"] = sky_conditions

                # Parse weather phenomena for this period
                weather_phenomena = []
                for weather_elem in period_elem.findall(".//weatherPhenomena"):
                    phenomenon = {
                        "code": self._get_text(weather_elem, ".//code"),
                        "intensity": self._get_text(weather_elem, ".//intensity"),
                        "descriptor": self._get_text(weather_elem, ".//descriptor"),
                        "proximity": self._get_text(weather_elem, ".//proximity"),
                    }
                    weather_phenomena.append(phenomenon)
                period["weather_phenomena"] = weather_phenomena

                forecast_periods.append(period)

            taf_data["forecast_periods"] = forecast_periods

            return {"type": "TAF", "data": taf_data}

        except Exception as e:
            self.logger.error(f"Error parsing TAF: {e}")
            return {"type": "TAF", "error": str(e)}

    def _parse_notam(self, root: etree.Element) -> Dict[str, Any]:
        """Parse NOTAM XML data"""
        try:
            notam_data = {}

            # Extract basic information
            notam_data["notam_id"] = self._get_text(
                root, ".//notamId"
            ) or self._get_text(root, ".//id")
            notam_data["notam_number"] = self._get_text(
                root, ".//notamNumber"
            ) or self._get_text(root, ".//number")
            notam_data["location_identifier"] = self._get_text(
                root, ".//locationIdentifier"
            ) or self._get_text(root, ".//location")
            notam_data["location_type"] = self._get_text(root, ".//locationType")

            # Parse timing
            notam_data["effective_from"] = self._parse_datetime(
                self._get_text(root, ".//effectiveFrom")
                or self._get_text(root, ".//effectiveTime/from")
            )
            notam_data["effective_until"] = self._parse_datetime(
                self._get_text(root, ".//effectiveUntil")
                or self._get_text(root, ".//effectiveTime/until")
            )

            # Parse content
            notam_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")
            notam_data["summary"] = self._get_text(root, ".//summary")
            notam_data["description"] = self._get_text(root, ".//description")

            # Parse classification
            notam_data["notam_type"] = self._get_text(root, ".//notamType")
            notam_data["priority"] = self._get_text(root, ".//priority")
            notam_data["category"] = self._get_text(root, ".//category")

            # Parse status
            notam_data["is_active"] = self._get_bool(root, ".//isActive", True)
            notam_data["is_cancelled"] = self._get_bool(root, ".//isCancelled", False)

            # Parse additional data
            notam_data["altitude_floor"] = self._get_int(root, ".//altitudeFloor")
            notam_data["altitude_ceiling"] = self._get_int(root, ".//altitudeCeiling")

            # Parse coordinates if available
            coordinates = {}
            lat_elem = root.find(".//latitude")
            lon_elem = root.find(".//longitude")
            if lat_elem is not None and lon_elem is not None:
                coordinates["latitude"] = self._get_float(lat_elem)
                coordinates["longitude"] = self._get_float(lon_elem)
            notam_data["coordinates"] = coordinates if coordinates else None

            return {"type": "NOTAM", "data": notam_data}

        except Exception as e:
            self.logger.error(f"Error parsing NOTAM: {e}")
            return {"type": "NOTAM", "error": str(e)}

    def _parse_sigmet(self, root: etree.Element) -> Dict[str, Any]:
        """Parse SIGMET XML data"""
        try:
            sigmet_data = {}

            # Extract basic information
            sigmet_data["alert_id"] = self._get_text(
                root, ".//sigmetId"
            ) or self._get_text(root, ".//id")
            sigmet_data["alert_type"] = "SIGMET"
            sigmet_data["severity"] = self._get_text(root, ".//severity")
            sigmet_data["urgency"] = self._get_text(root, ".//urgency")

            # Parse timing
            sigmet_data["valid_from"] = self._parse_datetime(
                self._get_text(root, ".//validFrom")
                or self._get_text(root, ".//validTime/from")
            )
            sigmet_data["valid_until"] = self._parse_datetime(
                self._get_text(root, ".//validUntil")
                or self._get_text(root, ".//validTime/until")
            )
            sigmet_data["issued_at"] = self._parse_datetime(
                self._get_text(root, ".//issueTime") or self._get_text(root, ".//time")
            )

            # Parse content
            sigmet_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")
            sigmet_data["summary"] = self._get_text(root, ".//summary")
            sigmet_data["description"] = self._get_text(root, ".//description")

            # Parse weather phenomena
            weather_phenomena = []
            for weather_elem in root.findall(".//weatherPhenomena"):
                phenomenon = {
                    "code": self._get_text(weather_elem, ".//code"),
                    "intensity": self._get_text(weather_elem, ".//intensity"),
                    "descriptor": self._get_text(weather_elem, ".//descriptor"),
                    "proximity": self._get_text(weather_elem, ".//proximity"),
                }
                weather_phenomena.append(phenomenon)
            sigmet_data["weather_phenomena"] = weather_phenomena

            # Parse altitude information
            sigmet_data["altitude_floor"] = self._get_int(root, ".//altitudeFloor")
            sigmet_data["altitude_ceiling"] = self._get_int(root, ".//altitudeCeiling")

            # Parse affected area
            affected_area = {}
            area_elem = root.find(".//affectedArea")
            if area_elem is not None:
                affected_area["description"] = self._get_text(
                    area_elem, ".//description"
                )
                affected_area["coordinates"] = self._get_text(
                    area_elem, ".//coordinates"
                )
            sigmet_data["affected_area"] = affected_area if affected_area else None

            # Parse affected airports
            affected_airports = []
            for airport_elem in root.findall(".//affectedAirport"):
                airport_code = self._get_text(airport_elem, ".//code")
                if airport_code:
                    affected_airports.append(airport_code)
            sigmet_data["affected_airports"] = (
                affected_airports if affected_airports else None
            )

            # Parse status
            sigmet_data["is_active"] = self._get_bool(root, ".//isActive", True)
            sigmet_data["is_cancelled"] = self._get_bool(root, ".//isCancelled", False)

            return {"type": "SIGMET", "data": sigmet_data}

        except Exception as e:
            self.logger.error(f"Error parsing SIGMET: {e}")
            return {"type": "SIGMET", "error": str(e)}

    def _parse_airmet(self, root: etree.Element) -> Dict[str, Any]:
        """Parse AIRMET XML data"""
        try:
            airmet_data = {}

            # Extract basic information
            airmet_data["alert_id"] = self._get_text(
                root, ".//airmetId"
            ) or self._get_text(root, ".//id")
            airmet_data["alert_type"] = "AIRMET"
            airmet_data["severity"] = self._get_text(root, ".//severity")
            airmet_data["urgency"] = self._get_text(root, ".//urgency")

            # Parse timing
            airmet_data["valid_from"] = self._parse_datetime(
                self._get_text(root, ".//validFrom")
                or self._get_text(root, ".//validTime/from")
            )
            airmet_data["valid_until"] = self._parse_datetime(
                self._get_text(root, ".//validUntil")
                or self._get_text(root, ".//validTime/until")
            )
            airmet_data["issued_at"] = self._parse_datetime(
                self._get_text(root, ".//issueTime") or self._get_text(root, ".//time")
            )

            # Parse content
            airmet_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")
            airmet_data["summary"] = self._get_text(root, ".//summary")
            airmet_data["description"] = self._get_text(root, ".//description")

            # Parse weather phenomena
            weather_phenomena = []
            for weather_elem in root.findall(".//weatherPhenomena"):
                phenomenon = {
                    "code": self._get_text(weather_elem, ".//code"),
                    "intensity": self._get_text(weather_elem, ".//intensity"),
                    "descriptor": self._get_text(weather_elem, ".//descriptor"),
                    "proximity": self._get_text(weather_elem, ".//proximity"),
                }
                weather_phenomena.append(phenomenon)
            airmet_data["weather_phenomena"] = weather_phenomena

            # Parse altitude information
            airmet_data["altitude_floor"] = self._get_int(root, ".//altitudeFloor")
            airmet_data["altitude_ceiling"] = self._get_int(root, ".//altitudeCeiling")

            # Parse affected area
            affected_area = {}
            area_elem = root.find(".//affectedArea")
            if area_elem is not None:
                affected_area["description"] = self._get_text(
                    area_elem, ".//description"
                )
                affected_area["coordinates"] = self._get_text(
                    area_elem, ".//coordinates"
                )
            airmet_data["affected_area"] = affected_area if affected_area else None

            # Parse affected airports
            affected_airports = []
            for airport_elem in root.findall(".//affectedAirport"):
                airport_code = self._get_text(airport_elem, ".//code")
                if airport_code:
                    affected_airports.append(airport_code)
            airmet_data["affected_airports"] = (
                affected_airports if affected_airports else None
            )

            # Parse status
            airmet_data["is_active"] = self._get_bool(root, ".//isActive", True)
            airmet_data["is_cancelled"] = self._get_bool(root, ".//isCancelled", False)

            return {"type": "AIRMET", "data": airmet_data}

        except Exception as e:
            self.logger.error(f"Error parsing AIRMET: {e}")
            return {"type": "AIRMET", "error": str(e)}

    def _parse_generic_weather(self, root: etree.Element) -> Dict[str, Any]:
        """Parse generic weather XML data"""
        try:
            weather_data = {}

            # Extract basic information
            weather_data["message_type"] = root.tag
            weather_data["timestamp"] = self._parse_datetime(
                self._get_text(root, ".//timestamp") or self._get_text(root, ".//time")
            )
            weather_data["raw_content"] = etree.tostring(root, encoding="unicode")

            # Extract all text content
            weather_data["content"] = {}
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    weather_data["content"][elem.tag] = elem.text.strip()

            return {"type": "GENERIC", "data": weather_data}

        except Exception as e:
            self.logger.error(f"Error parsing generic weather: {e}")
            return {"type": "GENERIC", "error": str(e)}

    def _parse_itws_alert(self, root: etree.Element) -> Dict[str, Any]:
        """Parse ITWS Alert XML data"""
        try:
            alert_data = {}

            # Extract basic information
            alert_data["alert_id"] = self._get_text(
                root, ".//alertId"
            ) or self._get_text(root, ".//id")
            alert_data["alert_type"] = "ITWS_ALERT"
            alert_data["center_id"] = self._get_text(root, ".//centerId")
            alert_data["airport_id"] = self._get_text(root, ".//airportId")
            alert_data["severity"] = self._get_text(root, ".//severity")
            alert_data["urgency"] = self._get_text(root, ".//urgency")

            # Parse timing
            alert_data["valid_from"] = self._parse_datetime(
                self._get_text(root, ".//validFrom")
                or self._get_text(root, ".//validTime/from")
            )
            alert_data["valid_until"] = self._parse_datetime(
                self._get_text(root, ".//validTo")
                or self._get_text(root, ".//validTime/until")
            )
            alert_data["issued_at"] = self._parse_datetime(
                self._get_text(root, ".//issuedAt")
                or self._get_text(root, ".//issueTime")
            )

            # Parse content
            alert_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")
            alert_data["summary"] = self._get_text(root, ".//summary")
            alert_data["description"] = self._get_text(root, ".//description")

            # Parse weather phenomena
            weather_phenomena = []
            for weather_elem in root.findall(".//weatherPhenomena"):
                phenomenon = {
                    "code": self._get_text(weather_elem, ".//code"),
                    "intensity": self._get_text(weather_elem, ".//intensity"),
                    "descriptor": self._get_text(weather_elem, ".//descriptor"),
                    "proximity": self._get_text(weather_elem, ".//proximity"),
                }
                weather_phenomena.append(phenomenon)
            alert_data["weather_phenomena"] = weather_phenomena

            # Parse affected area
            affected_area = {}
            area_elem = root.find(".//affectedArea")
            if area_elem is not None:
                affected_area["coordinates"] = self._get_text(
                    area_elem, ".//coordinates"
                )
                affected_area["radius"] = self._get_text(area_elem, ".//radius")
                affected_area["description"] = self._get_text(
                    area_elem, ".//description"
                )
            alert_data["affected_area"] = affected_area if affected_area else None

            # Parse affected airports
            affected_airports = []
            for airport_elem in root.findall(".//affectedAirport"):
                airport_code = self._get_text(airport_elem, ".//code")
                if airport_code:
                    affected_airports.append(airport_code)
            alert_data["affected_airports"] = (
                affected_airports if affected_airports else None
            )

            # Parse altitude information
            alert_data["altitude_floor"] = self._get_int(root, ".//altitudeFloor")
            alert_data["altitude_ceiling"] = self._get_int(root, ".//altitudeCeiling")

            # Parse status
            alert_data["is_active"] = self._get_bool(root, ".//isActive", True)
            alert_data["is_cancelled"] = self._get_bool(root, ".//isCancelled", False)

            return {"type": "ITWS_ALERT", "data": alert_data}

        except Exception as e:
            self.logger.error(f"Error parsing ITWS Alert: {e}")
            return {"type": "ITWS_ALERT", "error": str(e)}

    def _parse_itws(self, root: etree.Element) -> Dict[str, Any]:
        """Parse ITWS (Integrated Terminal Weather System) XML data"""
        try:
            itws_data = {}

            # Extract basic information
            itws_data["message_id"] = self._get_text(
                root, ".//messageId"
            ) or self._get_text(root, ".//id")
            itws_data["center_id"] = self._get_text(root, ".//centerId")
            itws_data["airport_id"] = self._get_text(root, ".//airportId")
            itws_data["message_type"] = self._get_text(root, ".//messageType")

            # Parse timing
            itws_data["timestamp"] = self._parse_datetime(
                self._get_text(root, ".//timestamp") or self._get_text(root, ".//time")
            )
            itws_data["valid_from"] = self._parse_datetime(
                self._get_text(root, ".//validFrom")
                or self._get_text(root, ".//validTime/from")
            )
            itws_data["valid_until"] = self._parse_datetime(
                self._get_text(root, ".//validTo")
                or self._get_text(root, ".//validTime/until")
            )

            # Parse content
            itws_data["raw_text"] = self._get_text(
                root, ".//rawText"
            ) or self._get_text(root, ".//text")
            itws_data["summary"] = self._get_text(root, ".//summary")
            itws_data["description"] = self._get_text(root, ".//description")

            # Parse weather data
            itws_data["wind_direction"] = self._get_int(root, ".//wind/direction")
            itws_data["wind_speed"] = self._get_int(root, ".//wind/speed")
            itws_data["wind_gust"] = self._get_int(root, ".//wind/gust")
            itws_data["visibility"] = self._get_float(root, ".//visibility/value")
            itws_data["visibility_units"] = self._get_text(root, ".//visibility/unit")
            itws_data["temperature"] = self._get_float(root, ".//temperature/value")
            itws_data["dewpoint"] = self._get_float(root, ".//dewpoint/value")
            itws_data["altimeter"] = self._get_float(root, ".//altimeter/value")

            # Parse sky conditions
            sky_conditions = []
            for sky_elem in root.findall(".//skyCondition"):
                sky_condition = {
                    "coverage": self._get_text(sky_elem, ".//coverage"),
                    "altitude": self._get_int(sky_elem, ".//altitude"),
                    "cloud_type": self._get_text(sky_elem, ".//cloudType"),
                }
                sky_conditions.append(sky_condition)
            itws_data["sky_conditions"] = sky_conditions

            # Parse weather phenomena
            weather_phenomena = []
            for weather_elem in root.findall(".//weatherPhenomena"):
                phenomenon = {
                    "code": self._get_text(weather_elem, ".//code"),
                    "intensity": self._get_text(weather_elem, ".//intensity"),
                    "descriptor": self._get_text(weather_elem, ".//descriptor"),
                    "proximity": self._get_text(weather_elem, ".//proximity"),
                }
                weather_phenomena.append(phenomenon)
            itws_data["weather_phenomena"] = weather_phenomena

            # Parse flight category
            itws_data["flight_category"] = self._get_text(root, ".//flightCategory")

            return {"type": "ITWS", "data": itws_data}

        except Exception as e:
            self.logger.error(f"Error parsing ITWS: {e}")
            return {"type": "ITWS", "error": str(e)}

    def _parse_itws_msg(self, root: etree.Element, message_type: str) -> Dict[str, Any]:
        """Parse ITWS message XML data"""
        try:
            itws_data = {}

            # Extract packet header information
            itws_data["packet_msgno"] = self._get_text(root, ".//packet_header_msgno")
            itws_data["packet_product"] = self._get_text(
                root, ".//packet_header_product"
            )
            itws_data["packet_size"] = self._get_text(
                root, ".//packet_header_packetsize"
            )

            # Extract product header information
            itws_data["product_msg_id"] = self._get_text(root, ".//product_msg_id")
            itws_data["product_msg_name"] = self._get_text(root, ".//product_msg_name")
            itws_data["product_type"] = self._get_text(
                root, ".//product_header_product_type"
            )
            itws_data["itws_sites"] = self._get_text(
                root, ".//product_header_itws_sites"
            )
            itws_data["airports"] = self._get_text(root, ".//product_header_airports")
            itws_data["source_id"] = self._get_text(root, ".//product_header_source_id")
            itws_data["source_type"] = self._get_text(
                root, ".//product_header_source_type"
            )

            # Parse timing information
            itws_data["generation_time"] = self._parse_datetime(
                self._get_text(root, ".//product_header_generation_time_seconds")
            )
            itws_data["expiration_time"] = self._parse_datetime(
                self._get_text(root, ".//product_header_expiration_time_seconds")
            )
            itws_data["received_time"] = self._parse_datetime(
                self._get_text(root, ".//product_header_received_time_seconds")
            )

            # Parse product-specific data based on message type
            if message_type == "ITWS_LIGHTNING":
                lightning_elem = root.find(".//lightning_warning")
                if lightning_elem is not None:
                    itws_data["lightning_enc"] = self._get_text(
                        lightning_elem, ".//lw_enc"
                    )
                    itws_data["alert_type"] = "LIGHTNING_WARNING"

            elif message_type == "ITWS_PRECIPITATION":
                precip_elem = root.find(".//precip")
                if precip_elem is not None:
                    itws_data["latitude"] = self._get_float(
                        precip_elem, ".//prcp_TRP_latitude"
                    )
                    itws_data["longitude"] = self._get_float(
                        precip_elem, ".//prcp_TRP_longitude"
                    )
                    itws_data["x_offset"] = self._get_int(
                        precip_elem, ".//prcp_xoffset"
                    )
                    itws_data["y_offset"] = self._get_int(
                        precip_elem, ".//prcp_yoffset"
                    )
                    itws_data["dx"] = self._get_int(precip_elem, ".//prcp_dx")
                    itws_data["dy"] = self._get_int(precip_elem, ".//prcp_dy")
                    itws_data["nrows"] = self._get_int(precip_elem, ".//prcp_nrows")
                    itws_data["ncols"] = self._get_int(precip_elem, ".//prcp_ncols")
                    itws_data["rotation"] = self._get_float(
                        precip_elem, ".//prcp_rotation"
                    )
                    itws_data["volume_scan_num"] = self._get_int(
                        precip_elem, ".//prcp_volume_scan_num"
                    )
                    itws_data["grid_compressed"] = self._get_text(
                        precip_elem, ".//prcp_grid_compressed"
                    )
                    itws_data["alert_type"] = "PRECIPITATION"

            elif message_type == "ITWS_MICROBURST":
                microburst_elem = root.find(".//microburst")
                if microburst_elem is not None:
                    itws_data["alert_type"] = "MICROBURST"
                    # Add microburst-specific parsing here

            elif message_type == "ITWS_TORNADO":
                tornado_elem = root.find(".//tornado")
                if tornado_elem is not None:
                    itws_data["alert_type"] = "TORNADO"
                    # Add tornado-specific parsing here

            elif message_type == "ITWS_GUST_FRONT":
                gust_elem = root.find(".//gust_front")
                if gust_elem is not None:
                    itws_data["alert_type"] = "GUST_FRONT"
                    # Add gust front-specific parsing here

            else:
                itws_data["alert_type"] = "GENERIC"

            # Set the message type
            itws_data["message_type"] = message_type

            # Create a unique alert ID from the message components
            alert_id = f"{itws_data.get('product_msg_id', 'UNKNOWN')}_{itws_data.get('itws_sites', 'UNKNOWN')}_{itws_data.get('airports', 'UNKNOWN')}"
            itws_data["alert_id"] = alert_id

            return {"type": message_type, "data": itws_data}

        except Exception as e:
            self.logger.error(f"Error parsing ITWS message: {e}")
            return {"type": message_type, "error": str(e)}

    def _get_text(self, root: etree.Element, xpath: str) -> Optional[str]:
        """Get text content from XML element"""
        try:
            elem = root.find(xpath)
            return elem.text.strip() if elem is not None and elem.text else None
        except:
            return None

    def _get_int(self, root: etree.Element, xpath: str) -> Optional[int]:
        """Get integer value from XML element"""
        try:
            text = self._get_text(root, xpath)
            return int(text) if text else None
        except:
            return None

    def _get_float(self, root: etree.Element, xpath: str) -> Optional[float]:
        """Get float value from XML element"""
        try:
            text = self._get_text(root, xpath)
            return float(text) if text else None
        except:
            return None

    def _get_bool(self, root: etree.Element, xpath: str, default: bool = False) -> bool:
        """Get boolean value from XML element"""
        try:
            text = self._get_text(root, xpath)
            if text:
                return text.lower() in ("true", "1", "yes", "on")
            return default
        except:
            return default

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string in various formats"""
        if not datetime_str:
            return None

        # Handle Unix timestamps (seconds since epoch)
        try:
            if datetime_str.isdigit() and len(datetime_str) >= 10:
                # Unix timestamp in seconds
                timestamp = int(datetime_str)
                # Handle both seconds and milliseconds
                if timestamp > 9999999999:  # milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
        except (ValueError, OSError):
            pass

        # Common datetime formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        # If no format matches, try to parse with dateutil
        try:
            from dateutil import parser

            return parser.parse(datetime_str)
        except:
            self.logger.warning(f"Could not parse datetime: {datetime_str}")
            return None
