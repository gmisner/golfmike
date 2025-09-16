#!/usr/bin/env python3
"""
Create Weather API Database Tables

This script creates the database tables for storing weather data from
the AviationWeather.gov API, separate from the ITWS real-time data.
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from db_config import connection_string
from models.sqlalchemy.weather_api import Base
from utils.logger import logger


def create_weather_api_tables():
    """Create all weather API tables"""
    try:
        # Create engine
        engine = create_engine(connection_string)

        logger.info("🌤️  Creating weather API database tables...")

        # Create all tables
        Base.metadata.create_all(engine)

        logger.info("✅ Weather API tables created successfully!")

        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%_api'
                ORDER BY table_name;
            """
                )
            )

            tables = [row[0] for row in result]
            logger.info(f"📊 Created tables: {', '.join(tables)}")

            # Get counts for each table
            for table in tables:
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    logger.info(f"   - {table}: {count} records")
                except Exception as e:
                    logger.warning(f"   - {table}: Error getting count - {e}")

        return True

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error creating weather API tables: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error creating weather API tables: {e}")
        return False


def verify_weather_api_tables():
    """Verify that weather API tables exist and are accessible"""
    try:
        engine = create_engine(connection_string)

        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'weather_stations_api',
                    'metar_data_api', 
                    'taf_data_api',
                    'pirep_data_api',
                    'weather_alerts_api',
                    'weather_observations_api'
                )
                ORDER BY table_name;
            """
                )
            )

            tables = [row[0] for row in result]

            if len(tables) == 6:
                logger.info("✅ All weather API tables exist and are accessible")
                return True
            else:
                missing_tables = set(
                    [
                        "weather_stations_api",
                        "metar_data_api",
                        "taf_data_api",
                        "pirep_data_api",
                        "weather_alerts_api",
                        "weather_observations_api",
                    ]
                ) - set(tables)

                logger.error(
                    f"❌ Missing weather API tables: {', '.join(missing_tables)}"
                )
                return False

    except Exception as e:
        logger.error(f"❌ Error verifying weather API tables: {e}")
        return False


if __name__ == "__main__":
    logger.info("🌤️  Weather API Database Setup")
    logger.info("=" * 50)

    # Create tables
    if create_weather_api_tables():
        logger.info("✅ Weather API tables created successfully!")

        # Verify tables
        if verify_weather_api_tables():
            logger.info("🎉 Weather API database setup complete!")
        else:
            logger.error("❌ Weather API database verification failed!")
            sys.exit(1)
    else:
        logger.error("❌ Failed to create weather API tables!")
        sys.exit(1)
