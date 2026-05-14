#!/usr/bin/env python3
"""Verify that route assignments are properly stored and linked"""

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
    print("📊 Database Status:")
    print("=" * 80)
    
    result = conn.execute(text("SELECT COUNT(*) FROM flights"))
    print(f"✅ Total flights: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM route_assignments"))
    print(f"✅ Total route assignments: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM route_waypoints"))
    print(f"✅ Total waypoints: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM aircraft"))
    print(f"✅ Total aircraft: {result.scalar()}")
    
    result = conn.execute(text("SELECT COUNT(*) FROM flight_alerts"))
    print(f"✅ Total alerts: {result.scalar()}")
    
    print("\n" + "=" * 80)
    print("\n🔗 Relationship Verification:")
    print("-" * 80)
    
    # Check if flights are linked to aircraft
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM flights f
        INNER JOIN aircraft a ON f.aircraft_id = a.aircraft_id
    """))
    print(f"✅ Flights linked to aircraft: {result.scalar()}")
    
    # Check if route assignments are linked to flights
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM route_assignments ra
        INNER JOIN flights f ON ra.gufi = f.gufi
    """))
    print(f"✅ Route assignments linked to flights: {result.scalar()}")
    
    # Check if waypoints are linked to route assignments
    result = conn.execute(text("""
        SELECT COUNT(*) 
        FROM route_waypoints rw
        INNER JOIN route_assignments ra ON rw.route_assignment_id = ra.id
    """))
    print(f"✅ Waypoints linked to route assignments: {result.scalar()}")
    
    print("\n" + "=" * 80)
    print("\n📋 Sample Data:")
    print("-" * 80)
    
    result = conn.execute(text("""
        SELECT 
            f.aircraft_id,
            f.gufi,
            f.flight_reference,
            f.departure_airport,
            f.arrival_airport,
            COUNT(DISTINCT ra.id) as route_count,
            COUNT(DISTINCT rw.id) as waypoint_count
        FROM flights f
        LEFT JOIN route_assignments ra ON f.gufi = ra.gufi
        LEFT JOIN route_waypoints rw ON ra.id = rw.route_assignment_id
        GROUP BY f.aircraft_id, f.gufi, f.flight_reference, f.departure_airport, f.arrival_airport
        ORDER BY route_count DESC
        LIMIT 5
    """))
    
    for row in result:
        print(f"\n  Aircraft: {row.aircraft_id}")
        print(f"  GUFI: {row.gufi}")
        print(f"  Flight Ref: {row.flight_reference}")
        print(f"  Route: {row.departure_airport} → {row.arrival_airport}")
        print(f"  Route Assignments: {row.route_count}")
        print(f"  Waypoints: {row.waypoint_count}")

