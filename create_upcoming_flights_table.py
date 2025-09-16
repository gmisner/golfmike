#!/usr/bin/env python3
"""
Script to create the upcoming_flights table in the database
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from utils.logger import main_logger as logger


def create_upcoming_flights_table():
    """Create the upcoming_flights table"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS upcoming_flights (
        id SERIAL PRIMARY KEY,
        aircraft_id VARCHAR(50) NOT NULL,
        gufi VARCHAR(50) UNIQUE,
        flight_reference VARCHAR(50),
        
        -- Flight details
        departure_airport VARCHAR(10),
        arrival_airport VARCHAR(10),
        departure_time TIMESTAMP WITH TIME ZONE,
        arrival_time TIMESTAMP WITH TIME ZONE,
        
        -- Aircraft information
        aircraft_type VARCHAR(50),
        aircraft_operator VARCHAR(100),
        
        -- Route information
        route_text TEXT,
        filed_route TEXT,
        
        -- Status and metadata
        status VARCHAR(50) DEFAULT 'PLANNED',
        source_facility VARCHAR(50),
        source_timestamp TIMESTAMP WITH TIME ZONE,
        
        -- Data source tracking
        data_source VARCHAR(50) DEFAULT 'SOLACE',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Additional flight plan data
        flight_plan_data TEXT
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_aircraft_id ON upcoming_flights(aircraft_id);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_gufi ON upcoming_flights(gufi);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_flight_reference ON upcoming_flights(flight_reference);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_departure_airport ON upcoming_flights(departure_airport);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_arrival_airport ON upcoming_flights(arrival_airport);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_departure_time ON upcoming_flights(departure_time);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_status ON upcoming_flights(status);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_aircraft_departure ON upcoming_flights(aircraft_id, departure_time);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_route ON upcoming_flights(departure_airport, arrival_airport);",
        "CREATE INDEX IF NOT EXISTS idx_upcoming_flights_status_time ON upcoming_flights(status, departure_time);"
    ]
    
    try:
        with engine.connect() as connection:
            # Create the table
            logger.info("Creating upcoming_flights table...")
            connection.execute(text(create_table_sql))
            connection.commit()
            logger.info("✅ upcoming_flights table created successfully")
            
            # Create indexes
            logger.info("Creating indexes for upcoming_flights table...")
            for index_sql in create_indexes_sql:
                connection.execute(text(index_sql))
            connection.commit()
            logger.info("✅ Indexes created successfully")
            
            # Verify table creation
            result = connection.execute(text("""
                SELECT COUNT(*) as table_exists 
                FROM information_schema.tables 
                WHERE table_name = 'upcoming_flights'
            """))
            
            table_exists = result.fetchone()[0]
            if table_exists:
                logger.info("✅ Table verification successful - upcoming_flights table exists")
            else:
                logger.error("❌ Table verification failed - upcoming_flights table not found")
                return False
                
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error creating upcoming_flights table: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error creating upcoming_flights table: {e}", exc_info=True)
        return False


def main():
    """Main function"""
    logger.info("🚀 Starting upcoming_flights table creation...")
    
    success = create_upcoming_flights_table()
    
    if success:
        logger.info("🎉 Successfully created upcoming_flights table and indexes!")
        print("✅ upcoming_flights table created successfully")
    else:
        logger.error("💥 Failed to create upcoming_flights table")
        print("❌ Failed to create upcoming_flights table")
        sys.exit(1)


if __name__ == "__main__":
    main()

