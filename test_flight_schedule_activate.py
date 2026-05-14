#!/usr/bin/env python3
"""Test the FlightScheduleActivate parser and storer with sample XML"""

from parsers.flight_schedule_activate_parser import parse_flight_schedule_activate
from parsers.xml_namespaces import parse_swim_xml_root
from storers.route_assignment_storer import store_route_assignments
from utils.logger import main_logger as logger

# Read sample XML file
with open("Sample XML/FlightScheduleActivate.xml", "r") as f:
    xml_data = f.read()

print("🔍 Testing FlightScheduleActivate parser...")
print("-" * 80)

# Parse the XML
parsed_data = parse_flight_schedule_activate(parse_swim_xml_root(xml_data))

print(f"✅ Parsed {len(parsed_data)} route assignments")
print()

if parsed_data:
    # Show first parsed record
    first = parsed_data[0]
    print("📋 First parsed route assignment:")
    print(f"   Aircraft ID: {first.get('aircraft_id')}")
    print(f"   GUFI: {first.get('gufi')}")
    print(f"   Flight Reference: {first.get('flight_reference')}")
    print(
        f"   Route: {first.get('departure_airport')} → {first.get('arrival_airport')}"
    )
    print(f"   Assigned Altitude: {first.get('assigned_altitude')} ft")
    print(f"   Assigned Speed: {first.get('assigned_speed')} kts")
    print(f"   Waypoints: {len(first.get('route_data', {}).get('waypoints', []))}")
    print(f"   Fixes: {len(first.get('route_data', {}).get('fixes', []))}")
    print()

    # Store in database
    print("💾 Storing route assignments in database...")
    try:
        store_route_assignments(parsed_data)
        print("✅ Successfully stored route assignments!")
        print()

        # Check what was stored
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
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM route_assignments
            """
                )
            )
            count = result.scalar()
            print(f"📊 Total route assignments in database: {count}")

            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM route_waypoints
            """
                )
            )
            waypoint_count = result.scalar()
            print(f"📊 Total waypoints in database: {waypoint_count}")

            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM flight_alerts WHERE alert_type = 'ROUTE_ASSIGNED'
            """
                )
            )
            alert_count = result.scalar()
            print(f"📊 Total route assignment alerts: {alert_count}")

            # Show sample route assignment
            result = conn.execute(
                text(
                    """
                SELECT ra.gufi, f.aircraft_id, ra.assigned_altitude, ra.assigned_speed,
                       (SELECT COUNT(*) FROM route_waypoints rw WHERE rw.route_assignment_id = ra.id) as waypoint_count
                FROM route_assignments ra
                LEFT JOIN flights f ON ra.gufi = f.gufi
                ORDER BY ra.assigned_at DESC
                LIMIT 5
            """
                )
            )

            print("\n📋 Sample stored route assignments:")
            for row in result:
                print(
                    f"   GUFI: {row.gufi}, Aircraft: {row.aircraft_id}, Alt: {row.assigned_altitude}ft, Speed: {row.assigned_speed}kts, Waypoints: {row.waypoint_count}"
                )

    except Exception as e:
        print(f"❌ Error storing route assignments: {e}")
        import traceback

        traceback.print_exc()
else:
    print("⚠️  No route assignments parsed from XML")
