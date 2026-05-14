#!/usr/bin/env python3
"""Check what aircraft have route assignments in the database"""

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
    # Check if route_assignments table has any data
    result = conn.execute(text("""
        SELECT COUNT(*) as count
        FROM route_assignments
    """))
    count = result.scalar()
    
    print(f"📊 Route Assignments in database: {count}")
    
    if count > 0:
        # Get all route assignments with flight info
        result = conn.execute(text("""
            SELECT 
                ra.gufi,
                f.aircraft_id,
                f.flight_reference,
                f.departure_airport,
                f.arrival_airport,
                ra.assigned_altitude,
                ra.assigned_speed,
                ra.source_facility,
                ra.assigned_at,
                (SELECT COUNT(*) FROM route_waypoints rw WHERE rw.route_assignment_id = ra.id) as waypoint_count
            FROM route_assignments ra
            LEFT JOIN flights f ON ra.gufi = f.gufi
            ORDER BY ra.assigned_at DESC
            LIMIT 50
        """))
        
        print("\n✅ Aircraft with Route Assignments:")
        print("-" * 100)
        
        for row in result:
            print(f"GUFI: {row.gufi}")
            print(f"  Aircraft ID: {row.aircraft_id or 'N/A'}")
            print(f"  Flight Reference: {row.flight_reference or 'N/A'}")
            print(f"  Route: {row.departure_airport or 'N/A'} → {row.arrival_airport or 'N/A'}")
            print(f"  Assigned Altitude: {row.assigned_altitude or 'N/A'} ft")
            print(f"  Assigned Speed: {row.assigned_speed or 'N/A'} kts")
            print(f"  Source Facility: {row.source_facility or 'N/A'}")
            print(f"  Assigned At: {row.assigned_at}")
            print(f"  Waypoints: {row.waypoint_count}")
            print("-" * 100)
    else:
        print("\n⚠️  No route assignments found in the database.")
        print("   The route_assignments table is empty.")
        print("   Route assignments are stored when FlightScheduleActivate XML messages are processed.")
        
        # Check if we have any flights at all
        result = conn.execute(text("SELECT COUNT(*) FROM flights"))
        flight_count = result.scalar()
        print(f"\n   Total flights in database: {flight_count}")
        
        # Check if we have any track updates
        result = conn.execute(text("SELECT COUNT(*) FROM track_updates"))
        track_count = result.scalar()
        print(f"   Total track updates in database: {track_count}")
        
        # Check upcoming_flights table to see if there's data there
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'upcoming_flights'
        """))
        if result.scalar() > 0:
            result = conn.execute(text("SELECT COUNT(*) FROM upcoming_flights"))
            upcoming_count = result.scalar()
            print(f"   Total flights in upcoming_flights table: {upcoming_count}")

