# tasks.py
from celery import shared_task
from utils.logger import main_logger as logger
from sqlalchemy.orm import Session
from swim_data_processor import parse_xml
from db_config import SessionLocal  # Import SessionLocal from db_config


@shared_task(bind=True)
def process_xml(self, xml_string):
    # Create a new session for this task
    session = SessionLocal()
    try:
        logger.info(f"Starting task {self.request.id} with XML payload.")

        # Process the XML and store results in the database
        logger.info("Parsing XML data...")
        parsed_data = parse_xml(xml_string)  # Use parse_xml to parse the XML string
        logger.info(f"Parsed data: {parsed_data}")

        # Example: Saving parsed data into the database
        logger.info("Saving parsed data into the database...")
        session.add(parsed_data)
        session.commit()
        logger.info(f"Task {self.request.id} completed successfully.")
        return {"status": "completed", "data": parsed_data}
    except Exception as e:
        logger.error(f"Error in task {self.request.id}: {e}", exc_info=True)
        session.rollback()
        raise self.retry(exc=e, countdown=60, max_retries=3)
    finally:
        logger.info("Closing database session.")
        session.close()
        SessionLocal.remove()  # Remove the session from the scoped registry
