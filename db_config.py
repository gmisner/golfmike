# db_config.py
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine.url import URL
from utils.logger import main_logger as logger  # Import your loguru logger
import logging

# Add the project root to the PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base  # Import Base from models

# URL configuration for local PostgreSQL server
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

# Create an engine with optimized connection pooling
engine = create_engine(
    connection_string,
    pool_size=10,  # Base pool size (2x number of workers)
    max_overflow=20,  # Allow more overflow for burst traffic
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=10,  # Faster timeout for getting connections
    pool_pre_ping=True,  # Validate connections before use
    echo=False,  # Disable query logging in production
    connect_args={
        "options": "-c default_transaction_isolation=read\\ committed"
    },  # Optimize transaction isolation
)

# Create a scoped session
SessionLocal = scoped_session(sessionmaker(autoflush=False, bind=engine))

# Enable SQLAlchemy logging via Python logging module
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


# Create tables
def init_db():
    logger.info("Initializing the database...")  # Log database initialization start
    Base.metadata.create_all(bind=engine)
    logger.success("Database initialized with tables.")


if __name__ == "__main__":
    logger.info("Starting database initialization from main...")  # Log main start
    init_db()
    logger.info("Database initialization completed.")  # Log main completion
