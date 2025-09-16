from celery import shared_task
from utils.logger import main_logger as logger
from db_config import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
from swim_data_processor import parse_and_store_to_database
import solace_consumer
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
    logger.info("Starting the Solace consumer using Celery...")
    try:
        solace_consumer.run()  # This is where the consumer starts
        logger.info("Solace consumer started successfully.")
    except Exception as e:
        logger.error(f"Error running solace consumer: {e}", exc_info=True)


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
                'KLAX', 'KJFK', 'KORD', 'KDFW', 'KATL', 'KSEA', 'KDEN', 
                'KIAH', 'KLAS', 'KMIA', 'KBOS', 'KPHX', 'KMSP', 'KDTW',
                'KPHL', 'KCLT', 'KMCO', 'KTPA', 'KPDX', 'KSLC'
            ]
        
        results = fetcher.fetch_and_store_all(station_ids=station_ids, bbox=bbox)
        
        total_records = sum(results.values())
        logger.info(f"✅ AviationWeather.gov fetch complete: {total_records} total records stored")
        
        return {
            "status": "success",
            "records_stored": results,
            "total_records": total_records,
            "timestamp": logger.info("Weather fetch completed at %s", str(datetime.now()))
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
    logger.info(f"🌤️  Fetching weather for flight route: {departure_airport} → {arrival_airport}")
    
    try:
        fetcher = AviationWeatherFetcher()
        
        # Collect all airports for this route
        airports = [departure_airport, arrival_airport]
        if route_airports:
            airports.extend(route_airports)
        
        # Remove duplicates
        airports = list(set(airports))
        
        results = fetcher.fetch_and_store_all(station_ids=airports)
        
        logger.info(f"✅ Flight weather fetch complete for {departure_airport} → {arrival_airport}: {sum(results.values())} records")
        
        return {
            "status": "success",
            "route": f"{departure_airport} → {arrival_airport}",
            "airports": airports,
            "records_stored": results,
            "total_records": sum(results.values())
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching flight weather for {departure_airport} → {arrival_airport}: {e}", exc_info=True)
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
    logger.info(f"🧹 Starting cleanup of weather data older than {days_to_keep} days...")
    
    try:
        session = SessionLocal()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean up old METAR data
        metar_deleted = session.query(METARData).filter(
            METARData.observation_time < cutoff_date
        ).delete()
        
        # Clean up old TAF data
        taf_deleted = session.query(TAFData).filter(
            TAFData.issue_time < cutoff_date
        ).delete()
        
        # Clean up old weather alerts (keep ITWS alerts longer)
        alert_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)  # Keep ITWS alerts for 60 days
        alert_deleted = session.query(WeatherAlert).filter(
            WeatherAlert.issued_at < alert_cutoff,
            WeatherAlert.alert_type.like('ITWS_%') == False  # Don't delete ITWS alerts
        ).delete()
        
        session.commit()
        
        total_deleted = metar_deleted + taf_deleted + alert_deleted
        logger.info(f"✅ Weather data cleanup complete: {total_deleted} records deleted")
        logger.info(f"   - METARs: {metar_deleted}")
        logger.info(f"   - TAFs: {taf_deleted}")
        logger.info(f"   - Weather Alerts: {alert_deleted}")
        
        return {
            "status": "success",
            "total_deleted": total_deleted,
            "metar_deleted": metar_deleted,
            "taf_deleted": taf_deleted,
            "alert_deleted": alert_deleted,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error in weather data cleanup: {e}", exc_info=True)
        raise
    finally:
        session.close()
