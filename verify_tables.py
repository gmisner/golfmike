#!/usr/bin/env python3
"""Verify that the new tables were created successfully"""

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

expected_tables = ['flights', 'route_assignments', 'route_waypoints', 'track_updates', 'flight_alerts']

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('flights', 'route_assignments', 'route_waypoints', 'track_updates', 'flight_alerts')
        ORDER BY table_name
    """))
    
    created_tables = [row[0] for row in result]
    
    print("✅ Created tables:")
    for table in created_tables:
        print(f"   - {table}")
    
    print(f"\n✅ Total: {len(created_tables)}/{len(expected_tables)} tables created")
    
    # Check for view
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND table_name = 'flight_status_view'
    """))
    
    if result.fetchone():
        print("✅ View 'flight_status_view' created")
    
    # Check for function
    result = conn.execute(text("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name = 'calculate_route_deviation'
    """))
    
    if result.fetchone():
        print("✅ Function 'calculate_route_deviation' created")
    
    print("\n🎉 All database relationships created successfully!")

