from celery import shared_task
from utils.logger import main_logger as logger
from db_config import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
from swim_data_processor import parse_and_store_to_database
import solace_consumer


# Process XML task, assigned to the 'message_processing' queue
@shared_task(bind=True, name="tasks.process_xml", queue="message_processing")
def process_xml(self, xml_string):
    try:
        logger.debug(f"Task {self.request.id} started with XML payload.")

        # Process the XML and store results using swim_data_processor
        logger.info("Processing XML data using swim_data_processor...")
        success = parse_and_store_to_database(
            xml_string
        )  # Use swim_data_processor to parse and store XML data

        if success:
            logger.info(f"Task {self.request.id} completed successfully.")
            return {"status": "completed"}
        else:
            logger.error(
                f"Task {self.request.id} failed to process and store the XML data."
            )
            return {"status": "failed"}
    except Exception as e:
        logger.error(f"Error in task {self.request.id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60, max_retries=3)


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
