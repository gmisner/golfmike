# db_config.py
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from utils.logger import main_logger as logger

# Add the project root to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base  # Import Base from models
from models.sqlalchemy import (
    AircraftDBModel,
    FlightPlanDBModel,
    TmiUpdatesDBModel,
    TrackInformationDBModel,
    StatusDBModel,
    FxaFlightDBModel,
)

# URL configuration for local PostgreSQL server
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.success("Database initialized with tables.")


# Run this function to create all tables
if __name__ == "__main__":
    init_db()
