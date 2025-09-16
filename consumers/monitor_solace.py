#!/usr/bin/env python3
"""
Solace Connection Monitor
Simple script to monitor Solace connection health and data flow
"""

import time
import subprocess
import psycopg2
from datetime import datetime, timedelta
from utils.logger import main_logger as logger


def check_database_connection():
    """Check if database is accessible and get latest track data"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="15432",
            database="postgres",
            user="postgres",
            password="postgres",
        )
        cursor = conn.cursor()

        # Get latest track data
        cursor.execute(
            """
            SELECT COUNT(*) as total_tracks, 
                   MAX(time_at_position) as latest_track,
                   COUNT(CASE WHEN time_at_position > NOW() - INTERVAL '5 minutes' THEN 1 END) as recent_tracks
            FROM track_information
        """
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return {
            "total_tracks": result[0],
            "latest_track": result[1],
            "recent_tracks": result[2],
            "status": "connected",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_solace_container():
    """Check if Solace container is running"""
    try:
        result = subprocess.run(
            [
                "docker-compose",
                "-f",
                ".devcontainer/docker-compose.yml",
                "ps",
                "bigtitties",
            ],
            capture_output=True,
            text=True,
            cwd="/Users/gmisner/Documents/GolfMike",
        )

        if "Up" in result.stdout:
            return {"status": "running"}
        else:
            return {"status": "stopped"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    """Main monitoring function"""
    logger.info("Starting Solace Connection Monitor")

    while True:
        try:
            # Check database
            db_status = check_database_connection()

            # Check container
            container_status = check_solace_container()

            # Log status
            if db_status["status"] == "connected":
                latest_track = db_status["latest_track"]
                recent_tracks = db_status["recent_tracks"]
                total_tracks = db_status["total_tracks"]

                # Check if data is recent (within last 5 minutes)
                if latest_track:
                    latest_time = (
                        latest_track.replace(tzinfo=None)
                        if hasattr(latest_track, "replace")
                        else latest_track
                    )
                    time_diff = datetime.now() - latest_time

                    if time_diff < timedelta(minutes=5):
                        logger.info(
                            f"✅ Data flowing: {total_tracks} total tracks, {recent_tracks} recent, latest: {latest_track}"
                        )
                    else:
                        logger.warning(
                            f"⚠️  Data stale: {total_tracks} total tracks, latest: {latest_track} ({time_diff} ago)"
                        )
                else:
                    logger.warning("⚠️  No track data found")
            else:
                logger.error(
                    f"❌ Database error: {db_status.get('error', 'Unknown error')}"
                )

            if container_status["status"] == "running":
                logger.info("✅ Solace container is running")
            else:
                logger.error(
                    f"❌ Solace container issue: {container_status.get('error', 'Container not running')}"
                )

            # Wait before next check
            time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()



