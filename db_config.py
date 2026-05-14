import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from utils.logger import main_logger as logger
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base

# Build URL from DATABASE_URL env var (preferred) or individual component vars
_database_url = os.getenv("DATABASE_URL") or (
    "postgresql+psycopg2://"
    f"{os.getenv('DB_USER', 'postgres')}:"
    f"{os.getenv('DB_PASSWORD', 'password')}@"
    f"{os.getenv('DB_HOST', 'postgres')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'postgres')}"
)

engine = create_engine(
    _database_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=10,
    pool_pre_ping=True,
    echo=False,
    connect_args={"options": "-c default_transaction_isolation=read\\ committed"},
)

SessionLocal = scoped_session(sessionmaker(autoflush=False, bind=engine))

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def init_db():
    logger.info("Initializing the database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized.")


if __name__ == "__main__":
    init_db()
