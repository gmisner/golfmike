#!/usr/bin/env python3
"""
Simple script to create the upcoming_flights table using the same connection as simple_api.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL

# Database connection (same as simple_api.py)
connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)

create_table_sql = """
CREATE TABLE IF NOT EXISTS upcoming_flights (
    id SERIAL PRIMARY KEY,
    aircraft_id VARCHAR(50) NOT NULL,
    gufi VARCHAR(50) UNIQUE,
    flight_reference VARCHAR(50),
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    departure_time TIMESTAMP WITH TIME ZONE,
    arrival_time TIMESTAMP WITH TIME ZONE,
    aircraft_type VARCHAR(50),
    aircraft_operator VARCHAR(100),
    route_text TEXT,
    filed_route TEXT,
    status VARCHAR(50) DEFAULT 'PLANNED',
    source_facility VARCHAR(50),
    source_timestamp TIMESTAMP WITH TIME ZONE,
    data_source VARCHAR(50) DEFAULT 'SOLACE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
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

if __name__ == "__main__":
    try:
        with engine.connect() as connection:
            print("Creating upcoming_flights table...")
            connection.execute(text(create_table_sql))
            connection.commit()
            print("✅ Table created successfully")
            
            print("Creating indexes...")
            for index_sql in create_indexes_sql:
                connection.execute(text(index_sql))
            connection.commit()
            print("✅ Indexes created successfully")
            
            # Verify
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'upcoming_flights'
                )
            """))
            if result.scalar():
                print("✅ Table verification successful")
            else:
                print("❌ Table verification failed")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

