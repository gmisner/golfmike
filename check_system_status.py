#!/usr/bin/env python3
"""
System Status Checker for GolfMike Flight Tracker

This script checks the status of all system components and provides
a comprehensive report on why flights might not be visible.
"""

import sys
import os

sys.path.append("/app")


def check_database_connection():
    """Check database connection and data"""
    try:
        from db_config import SessionLocal
        from sqlalchemy import text

        session = SessionLocal()

        # Check basic connection
        result = session.execute(text("SELECT 1 as test"))
        print("✅ Database connection: OK")

        # Check track_information table
        result = session.execute(
            text("SELECT COUNT(*) as count FROM track_information")
        )
        track_count = result.scalar()
        print(f"📊 Track records: {track_count}")

        # Check aircraft table
        result = session.execute(text("SELECT COUNT(*) as count FROM aircraft"))
        aircraft_count = result.scalar()
        print(f"✈️  Aircraft records: {aircraft_count}")

        # Check recent tracks with valid coordinates
        result = session.execute(
            text(
                """
            SELECT COUNT(*) as count 
            FROM track_information 
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL 
            AND latitude != '' 
            AND longitude != ''
            AND time_at_position > NOW() - INTERVAL '1 hour'
        """
            )
        )
        recent_tracks = result.scalar()
        print(f"📍 Recent valid tracks (1 hour): {recent_tracks}")

        # Check unique aircraft with recent data
        result = session.execute(
            text(
                """
            SELECT COUNT(DISTINCT aircraft_id) as count 
            FROM track_information 
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL 
            AND latitude != '' 
            AND longitude != ''
            AND time_at_position > NOW() - INTERVAL '1 hour'
        """
            )
        )
        recent_aircraft = result.scalar()
        print(f"✈️  Aircraft with recent data: {recent_aircraft}")

        session.close()
        return recent_tracks > 0

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_solace_consumer():
    """Check if Solace consumer is running and processing data"""
    try:
        import subprocess

        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=golfmike-traffic-consumer",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            print("✅ Solace consumer: Running")
            return True
        else:
            print("❌ Solace consumer: Not running")
            return False
    except Exception as e:
        print(f"❌ Error checking Solace consumer: {e}")
        return False


def check_flask_app():
    """Check if Flask app is running"""
    try:
        import requests

        response = requests.get("http://localhost:5500/", timeout=5)
        if response.status_code == 200:
            print("✅ Flask app: Running")
            return True
        else:
            print(f"❌ Flask app: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Flask app: Not accessible - {e}")
        return False


def check_api_endpoints():
    """Check if API endpoints are working"""
    try:
        import requests

        response = requests.get("http://localhost:5500/api/flights", timeout=5)
        if response.status_code == 200:
            data = response.json()
            flight_count = len(data) if isinstance(data, list) else 0
            print(f"✅ API endpoints: Working ({flight_count} flights)")
            return True
        else:
            print(f"❌ API endpoints: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API endpoints: Error - {e}")
        return False


def main():
    print("🔍 GolfMike Flight Tracker - System Status Check")
    print("=" * 60)

    # Check all components
    db_ok = check_database_connection()
    solace_ok = check_solace_consumer()
    flask_ok = check_flask_app()
    api_ok = check_api_endpoints()

    print("\n📋 System Status Summary:")
    print("=" * 30)

    if not db_ok:
        print("❌ Database: No recent flight data found")
        print("   → Check if Solace consumer is receiving FAA SWIM data")
        print("   → Verify database connection and tables")

    if not solace_ok:
        print("❌ Solace Consumer: Not running")
        print(
            "   → Start with: docker compose -f .devcontainer/docker-compose.yml up traffic_consumer -d"
        )

    if not flask_ok:
        print("❌ Flask App: Not accessible")
        print(
            "   → Start with: docker-compose -f .devcontainer/docker-compose.yml up web_api -d"
        )

    if not api_ok:
        print("❌ API Endpoints: Not working")
        print("   → Check Flask app logs for errors")

    if all([db_ok, solace_ok, flask_ok, api_ok]):
        print("✅ All systems operational!")
        print("   → Flights should be visible in the web interface")
    else:
        print("\n🔧 Troubleshooting Steps:")
        print(
            "1. Start all services: docker-compose -f .devcontainer/docker-compose.yml up -d"
        )
        print("2. Check traffic consumer logs: docker logs golfmike-traffic-consumer")
        print("3. Check Flask app logs: docker logs golfmike-web-api")
        print("4. Wait 5-10 minutes for FAA SWIM data to populate")
        print("5. Access the web interface at: http://localhost:5500")


if __name__ == "__main__":
    main()
