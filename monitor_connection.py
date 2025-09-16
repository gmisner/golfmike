#!/usr/bin/env python3
"""
Simple script to monitor Solace connection status
"""
import time
import requests
from datetime import datetime, timedelta


def check_solace_connection():
    """Check if Solace consumer is receiving messages"""
    try:
        # Check the health endpoint
        response = requests.get("http://localhost:5500/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ System Health: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to health endpoint: {e}")


def check_recent_messages():
    """Check for recent flight notifications"""
    try:
        # Check for recent notifications (last 5 minutes)
        response = requests.get(
            "http://localhost:5500/api/flights/notifications?hours=0.1", timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            print(f"📡 Recent notifications (last 6 minutes): {count}")

            if count > 0:
                print("✅ Messages are being processed!")
            else:
                print("⚠️  No recent messages - connection may be idle")
        else:
            print(f"❌ Failed to get notifications: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to notifications endpoint: {e}")


def main():
    """Main monitoring loop"""
    print("🔍 GolfMike Connection Monitor")
    print("=" * 40)

    while True:
        print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        check_solace_connection()
        check_recent_messages()

        print("\n" + "-" * 40)
        print("Press Ctrl+C to stop monitoring")

        try:
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
            break


if __name__ == "__main__":
    main()



