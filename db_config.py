# db_config.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL configuration with the correct endpoint ID
connection_string = "postgresql://gkmisner:81QgOfuHCwyk@ep-tight-lake-32732521.us-west-2.aws.neon.tech:5432/swim"

engine = create_engine(connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from models.sqlalchemy import (
        AircraftDBModel,
        FlightPlanDBModel,
        TmiUpdatesDBModel,
        TrackDBModel,
        StatusDBModel,
        FxaUpdatesDBModel,
    )

    Base.metadata.create_all(bind=engine)


# Run this function to create all tables
if __name__ == "__main__":
    init_db()
