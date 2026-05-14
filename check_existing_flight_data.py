#!/usr/bin/env python3
"""Check existing flight data in various tables to see what we have"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL

connection_string = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="postgres",
)

engine = create_engine(connection_string)

with engine.connect() as conn:
    print("🔍 Checking existing flight data in database...\n")
    
    # Check flight_plan table
    result = conn.execute(text("""
        SELECT COUNT(*) as count,
               COUNT(DISTINCT gufi) as unique_gufis,
               COUNT(DISTINCT aircraft_id) as unique_aircraft
        FROM flight_plan
    """))
    row = result.fetchone()
    print(f"📋 flight_plan table:")
    print(f"   Total records: {row[0]}")
    print(f"   Unique GUFIs: {row[1]}")
    print(f"   Unique Aircraft: {row[2]}")
    
    if row[0] > 0:
        # Get sample records
        result = conn.execute(text("""
            SELECT gufi, aircraft_id, departure_airport, arrival_airport, igtd
            FROM flight_plan
            WHERE gufi IS NOT NULL
            LIMIT 5
        """))
        print("   Sample records:")
        for r in result:
            print(f"     - GUFI: {r.gufi}, Aircraft: {r.aircraft_id}, Route: {r.departure_airport} → {r.arrival_airport}")
    
    # Check track_information table
    result = conn.execute(text("""
        SELECT COUNT(*) as count,
               COUNT(DISTINCT gufi) as unique_gufis,
               COUNT(DISTINCT aircraft_id) as unique_aircraft
        FROM track_information
    """))
    row = result.fetchone()
    print(f"\n📡 track_information table:")
    print(f"   Total records: {row[0]}")
    print(f"   Unique GUFIs: {row[1]}")
    print(f"   Unique Aircraft: {row[2]}")
    
    if row[0] > 0:
        # Get sample records
        result = conn.execute(text("""
            SELECT gufi, aircraft_id, departure_airport, arrival_airport, time_at_position
            FROM track_information
            WHERE gufi IS NOT NULL
            LIMIT 5
        """))
        print("   Sample records:")
        for r in result:
            print(f"     - GUFI: {r.gufi}, Aircraft: {r.aircraft_id}, Route: {r.departure_airport} → {r.arrival_airport}")
    
    # Check upcoming_flights table
    result = conn.execute(text("""
        SELECT COUNT(*) as count
        FROM information_schema.tables 
        WHERE table_name = 'upcoming_flights'
    """))
    if result.scalar() > 0:
        result = conn.execute(text("""
            SELECT COUNT(*) as count,
                   COUNT(DISTINCT gufi) as unique_gufis,
                   COUNT(DISTINCT aircraft_id) as unique_aircraft
            FROM upcoming_flights
        """))
        row = result.fetchone()
        print(f"\n✈️  upcoming_flights table:")
        print(f"   Total records: {row[0]}")
        print(f"   Unique GUFIs: {row[1]}")
        print(f"   Unique Aircraft: {row[2]}")
        
        if row[0] > 0:
            # Get sample records
            result = conn.execute(text("""
                SELECT gufi, aircraft_id, departure_airport, arrival_airport, status, departure_time
                FROM upcoming_flights
                WHERE gufi IS NOT NULL
                ORDER BY departure_time DESC
                LIMIT 5
            """))
            print("   Sample records:")
            for r in result:
                print(f"     - GUFI: {r.gufi}, Aircraft: {r.aircraft_id}, Route: {r.departure_airport} → {r.arrival_airport}, Status: {r.status}")
    
    # Check if there are any XML messages that might contain FlightScheduleActivate data
    print(f"\n📝 Summary:")
    print(f"   The new relationship tables (flights, route_assignments, etc.) are empty.")
    print(f"   To populate route_assignments, you need to:")
    print(f"   1. Process FlightScheduleActivate XML messages")
    print(f"   2. Parse the route data (waypoints, fixes, assigned altitude/speed)")
    print(f"   3. Store in route_assignments table using the ALERT_SYSTEM_EXAMPLE.py functions")

