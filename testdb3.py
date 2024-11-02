import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import main_logger as logger
import logging

# Add the project root to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import Base, AircraftDBModel, FlightPlanDBModel

# Database Configuration
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(
    connection_string,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=30,
    echo=True,
)

SessionLocal = scoped_session(sessionmaker(autoflush=False, bind=engine))

# Enable SQLAlchemy logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


def init_db():
    logger.info("Attempting to initialize the database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.success("Database initialized successfully with tables.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def test_connection():
    logger.info("Attempting to connect to the database...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def insert_sample_data():
    logger.info("Attempting to insert sample data...")
    session = SessionLocal()
    try:
        # Sample aircraft
        aircraft = AircraftDBModel(aircraft_id="SAMPLE001")
        session.add(aircraft)
        logger.info("Added sample aircraft to session.")

        # Sample flight plan
        flight_plan = FlightPlanDBModel(
            flight_plan_id="GUFI001",
            gufi="GUFI001",
            aircraft_id="SAMPLE001",
            igtd="2023-01-01 12:00:00",
            departure_airport="LAX",
            arrival_airport="JFK",
        )
        session.add(flight_plan)
        logger.info("Added sample flight plan to session.")

        # Attempt to commit changes
        logger.info("Attempting to commit changes...")
        session.commit()
        logger.success("Sample data inserted successfully.")
    except SQLAlchemyError as e:
        logger.error(f"Error inserting sample data: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    try:
        logger.info("Starting database operations...")

        # Initialize database
        init_db()

        # Test connection
        test_connection()

        # Insert sample data
        insert_sample_data()

        logger.info("All database operations completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred during database operations: {e}")
    finally:
        logger.info("Database operations script finished.")


if __name__ == "__main__":
    main()
