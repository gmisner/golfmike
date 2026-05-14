#!/usr/bin/env python3
"""Check the relationship between aircraft_id and flight_plan to find GUFIs"""

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

# Sample aircraft IDs from FlightScheduleActivate
sample_aircraft = ['UAL68', 'JZA7939', 'HAL204', 'JZA441', 'NKS523']

with engine.connect() as conn:
    print("🔍 Checking flight plan relationships for sample aircraft...\n")
    
    for aircraft_id in sample_aircraft:
        result = conn.execute(
            text("""
                SELECT aircraft_id, gufi, flight_reference, departure_airport, arrival_airport, igtd
                FROM flight_plan 
                WHERE aircraft_id = :aircraft_id
                ORDER BY id DESC
                LIMIT 3
            """),
            {"aircraft_id": aircraft_id}
        )
        
        rows = result.fetchall()
        if rows:
            print(f"✅ Found {len(rows)} flight plan(s) for {aircraft_id}:")
            for row in rows:
                print(f"   GUFI: {row[1]}, Flight Ref: {row[2]}, Route: {row[3]} → {row[4]}")
        else:
            print(f"⚠️  No flight plan found for {aircraft_id}")
    
    print("\n" + "="*80)
    print("\n💡 Solution: Since flight_plan has aircraft_id as a foreign key,")
    print("   we can look up GUFI by aircraft_id when processing FlightScheduleActivate.")
    print("   The route assignment should be linked to the flight via GUFI.")
    print("\n   Relationship chain:")
    print("   FlightScheduleActivate → aircraft_id → flight_plan → GUFI → route_assignments")

