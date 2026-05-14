from celery import shared_task
from utils.logger import main_logger as logger
from db_config import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
from swim_data_processor import parse_and_store_to_database

# import solace_consumer  # Moved to consumers/traffic_consumer.py
from aviation_weather_fetcher import AviationWeatherFetcher
from datetime import datetime, timedelta
from models.sqlalchemy.weather import METARData, TAFData, WeatherAlert


# Process XML task, assigned to the 'message_processing' queue
@shared_task(
    bind=True,
    name="tasks.process_xml",
    queue="message_processing",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,
)
def process_xml(self, xml_string):
    try:
        logger.debug(
            f"Task {self.request.id} started with XML payload (attempt {self.request.retries + 1})"
        )

        # Process the XML and store results using swim_data_processor
        success = parse_and_store_to_database(xml_string)

        if success:
            logger.info(f"Task {self.request.id} completed successfully.")
            return {"status": "completed", "task_id": self.request.id}
        else:
            logger.error(
                f"Task {self.request.id} failed to process and store the XML data."
            )
            raise Exception("Failed to process and store XML data")

    except Exception as e:
        logger.error(
            f"Error in task {self.request.id} (attempt {self.request.retries + 1}): {e}",
            exc_info=True,
        )
        raise  # Let Celery handle the retry logic


# Test database connection task (default queue assignment)
@shared_task(name="tasks.test_db")
def test_db():
    logger.info("Testing database connection from Celery worker...")
    try:
        with SessionLocal() as session:
            result = session.execute("SELECT 1")
            logger.info(f"Database test result: {result.fetchone()}")
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")


# Start Solace consumer task, assigned to the 'solace' queue
@shared_task(name="tasks.start_solace_consumer", queue="solace")
def start_solace_consumer():
    """Start the Solace consumer (legacy task - consumers now run as Docker services)"""
    logger.info("Starting the Solace consumer using Celery...")
    try:
        # Note: This task is now legacy - consumers run as Docker services
        # Import and run the traffic consumer directly
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "consumers/traffic_consumer.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Traffic consumer failed: {result.stderr}")
        else:
            logger.info("Traffic consumer started successfully")
    except Exception as e:
        logger.error(f"Error running solace consumer: {e}", exc_info=True)


# Process flight plan XML task
@shared_task(name="tasks.process_flight_plan_xml", queue="message_processing")
def process_flight_plan_xml(xml_string):
    """Process flight plan XML data from Solace queue"""
    logger.info("Processing flight plan XML data...")
    try:
        from parsers.flight_plan_parser import FlightPlanXMLParser
        from storers.upcoming_flight_storer import UpcomingFlightStorer
        from db_config import SessionLocal

        # Parse the XML data
        parser = FlightPlanXMLParser()
        flight_plan_data = parser.parse_flight_plan_xml(xml_string)

        if flight_plan_data:
            # Store the flight plan data
            storer = UpcomingFlightStorer()
            session = SessionLocal()

            try:
                success = storer.store_flight_plan(flight_plan_data, session)
                if success:
                    logger.info(
                        f"Successfully processed flight plan for aircraft: {flight_plan_data.get('aircraft_id')}"
                    )
                else:
                    logger.error("Failed to store flight plan data")
            finally:
                session.close()
        else:
            logger.warning("Failed to parse flight plan XML data")

    except Exception as e:
        logger.error(f"Error processing flight plan XML: {e}", exc_info=True)
        raise


# Start flight plan consumer task
@shared_task(name="tasks.start_flight_plan_consumer", queue="solace")
def start_flight_plan_consumer():
    logger.info("Starting the flight plan consumer using Celery...")
    try:
        import flight_plan_consumer

        flight_plan_consumer.run()  # This is where the flight plan consumer starts
        logger.info("Flight plan consumer started successfully.")
    except Exception as e:
        logger.error(f"Error running flight plan consumer: {e}", exc_info=True)


# Weather data fetch task, runs every 15 minutes
@shared_task(
    name="tasks.fetch_aviation_weather",
    queue="weather_processing",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def fetch_aviation_weather(station_ids=None, bbox=None):
    """
    Fetch weather data from AviationWeather.gov API and store in database

    Args:
        station_ids: List of ICAO station IDs to fetch data for
        bbox: Bounding box as "west,south,east,north" for regional data
    """
    logger.info("🌤️  Starting AviationWeather.gov data fetch task...")

    try:
        fetcher = AviationWeatherFetcher()

        # Default to major US airports if no specific request
        if not station_ids and not bbox:
            station_ids = [
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

        results = fetcher.fetch_and_store_all(station_ids=station_ids, bbox=bbox)

        total_records = sum(results.values())
        logger.info(
            f"✅ AviationWeather.gov fetch complete: {total_records} total records stored"
        )

        return {
            "status": "success",
            "records_stored": results,
            "total_records": total_records,
            "timestamp": logger.info(
                "Weather fetch completed at %s", str(datetime.now())
            ),
        }

    except Exception as e:
        logger.error(f"❌ Error in aviation weather fetch task: {e}", exc_info=True)
        raise


# Weather data fetch for specific flight route
@shared_task(
    name="tasks.fetch_flight_weather",
    queue="weather_processing",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def fetch_flight_weather(departure_airport, arrival_airport, route_airports=None):
    """
    Fetch weather data for a specific flight route

    Args:
        departure_airport: ICAO code of departure airport
        arrival_airport: ICAO code of arrival airport
        route_airports: List of ICAO codes for airports along the route
    """
    logger.info(
        f"🌤️  Fetching weather for flight route: {departure_airport} → {arrival_airport}"
    )

    try:
        fetcher = AviationWeatherFetcher()

        # Collect all airports for this route
        airports = [departure_airport, arrival_airport]
        if route_airports:
            airports.extend(route_airports)

        # Remove duplicates
        airports = list(set(airports))

        results = fetcher.fetch_and_store_all(station_ids=airports)

        logger.info(
            f"✅ Flight weather fetch complete for {departure_airport} → {arrival_airport}: {sum(results.values())} records"
        )

        return {
            "status": "success",
            "route": f"{departure_airport} → {arrival_airport}",
            "airports": airports,
            "records_stored": results,
            "total_records": sum(results.values()),
        }

    except Exception as e:
        logger.error(
            f"❌ Error fetching flight weather for {departure_airport} → {arrival_airport}: {e}",
            exc_info=True,
        )
        raise


# Cleanup old weather data task
@shared_task(
    name="tasks.cleanup_old_weather_data",
    queue="maintenance",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 300},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def cleanup_old_weather_data(days_to_keep=30):
    """
    Clean up old weather data to prevent database bloat

    Args:
        days_to_keep: Number of days of weather data to retain (default: 30)
    """
    logger.info(
        f"🧹 Starting cleanup of weather data older than {days_to_keep} days..."
    )

    try:
        session = SessionLocal()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Clean up old METAR data
        metar_deleted = (
            session.query(METARData)
            .filter(METARData.observation_time < cutoff_date)
            .delete()
        )

        # Clean up old TAF data
        taf_deleted = (
            session.query(TAFData).filter(TAFData.issue_time < cutoff_date).delete()
        )

        # Clean up old weather alerts (keep ITWS alerts longer)
        alert_cutoff = datetime.now() - timedelta(
            days=days_to_keep * 2
        )  # Keep ITWS alerts for 60 days
        alert_deleted = (
            session.query(WeatherAlert)
            .filter(
                WeatherAlert.issued_at < alert_cutoff,
                WeatherAlert.alert_type.like("ITWS_%")
                == False,  # Don't delete ITWS alerts
            )
            .delete()
        )

        session.commit()

        total_deleted = metar_deleted + taf_deleted + alert_deleted
        logger.info(
            f"✅ Weather data cleanup complete: {total_deleted} records deleted"
        )
        logger.info(f"   - METARs: {metar_deleted}")
        logger.info(f"   - TAFs: {taf_deleted}")
        logger.info(f"   - Weather Alerts: {alert_deleted}")

        return {
            "status": "success",
            "total_deleted": total_deleted,
            "metar_deleted": metar_deleted,
            "taf_deleted": taf_deleted,
            "alert_deleted": alert_deleted,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error in weather data cleanup: {e}", exc_info=True)
        raise
    finally:
        session.close()


@shared_task(name="tasks.refresh_flow_predictions", queue="weather_processing")
def refresh_flow_predictions(airport_icao_list=None):
    """
    Refresh flow control probability predictions for a list of airports.
    Runs every 15 minutes via Celery Beat.
    """
    from services.flow_probability_service import batch_predict

    if not airport_icao_list:
        airport_icao_list = ["KJFK", "KLAX", "KORD", "KDFW", "KATL"]

    logger.info(f"Refreshing flow predictions for {len(airport_icao_list)} airports")
    try:
        results = batch_predict(airport_icao_list, window_hours=2)
        high_risk = [r for r in results if (r.get("flow_probability") or 0) >= 0.55]
        if high_risk:
            logger.warning(
                f"HIGH/VERY_HIGH flow risk: "
                + ", ".join(f"{r['airport']} ({r['flow_probability']:.0%})" for r in high_risk)
            )
        return {
            "status": "success",
            "airports_processed": len(results),
            "high_risk_count": len(high_risk),
        }
    except Exception as e:
        logger.error(f"Flow prediction refresh failed: {e}", exc_info=True)
        raise


@shared_task(name="tasks.label_completed_flow_predictions", queue="maintenance")
def label_completed_flow_predictions():
    """
    Retrospectively label completed flow predictions with actual outcomes.

    For each prediction whose window has expired, checks whether TMI data
    contains a GDP/GS record for that airport during the prediction window.
    This builds the labeled training dataset for upgrading to an ML model.
    """
    from datetime import timezone
    from sqlalchemy import text

    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find unlabeled predictions whose window has closed
        unlabeled = session.execute(
            text(
                """
                SELECT id, airport_icao, predicted_at, window_hours
                FROM flow_predictions
                WHERE actual_flow_control IS NULL
                  AND predicted_at + (window_hours * INTERVAL '1 hour') < :now
                LIMIT 200
                """
            ),
            {"now": now},
        ).fetchall()

        labeled = 0
        for row in unlabeled:
            window_end = row.predicted_at + timedelta(hours=row.window_hours)

            # Check if any GDP/GS TMI program was active for this airport in that window
            tmi_hit = session.execute(
                text(
                    """
                    SELECT COUNT(*) as cnt
                    FROM tmi_updates
                    WHERE update_time BETWEEN :start AND :end
                      AND (
                        fca_id ILIKE :pattern
                        AND (update_type ILIKE '%GDP%' OR update_type ILIKE '%GS%')
                      )
                    """
                ),
                {
                    "start": row.predicted_at,
                    "end": window_end,
                    "pattern": f"%{row.airport_icao}%",
                },
            ).fetchone()

            had_flow = (tmi_hit.cnt > 0) if tmi_hit else False

            session.execute(
                text(
                    """
                    UPDATE flow_predictions
                    SET actual_flow_control = :val, labeled_at = :now
                    WHERE id = :id
                    """
                ),
                {"val": had_flow, "now": now, "id": row.id},
            )
            labeled += 1

        session.commit()
        logger.info(f"Labeled {labeled} completed flow predictions")
        return {"status": "success", "labeled": labeled}

    except Exception as e:
        session.rollback()
        logger.error(f"Flow prediction labeling failed: {e}", exc_info=True)
        raise
    finally:
        session.close()
