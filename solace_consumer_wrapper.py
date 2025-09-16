#!/usr/bin/env python3
"""
Solace Consumer Wrapper with Auto-Restart
This script wraps the Solace consumer and automatically restarts it when connection issues are detected.
"""

import time
import subprocess
import sys
from utils.logger import main_logger as logger


def run_solace_consumer():
    """Run the Solace consumer and return the exit code"""
    try:
        logger.info("🚀 WRAPPER - Starting Solace consumer process...")
        # Import and run the solace consumer
        from solace_consumer import run

        run()
        logger.info("✅ WRAPPER - Solace consumer exited normally")
        return 0
    except Exception as e:
        logger.error(f"❌ WRAPPER - Solace consumer error: {e}")
        logger.error(f"❌ WRAPPER - Error type: {type(e).__name__}")
        logger.error(f"❌ WRAPPER - Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1


def main():
    """Main wrapper function with auto-restart logic"""
    restart_count = 0
    max_restarts = 10  # Maximum number of restarts per hour
    restart_window = 3600  # 1 hour window
    restart_times = []

    logger.info(
        "🔄 WRAPPER - Starting Solace Consumer Wrapper with auto-restart capability"
    )
    logger.info(
        f"🔄 WRAPPER - Max restarts: {max_restarts} per {restart_window} seconds"
    )
    logger.info(f"🔄 WRAPPER - Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        try:
            logger.info(
                f"🔄 WRAPPER - Starting Solace consumer (attempt {restart_count + 1})"
            )
            logger.info(
                f"🔄 WRAPPER - Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Clean up old restart times outside the window
            current_time = time.time()
            restart_times = [
                t for t in restart_times if current_time - t < restart_window
            ]
            logger.info(
                f"🔄 WRAPPER - Recent restarts in window: {len(restart_times)}/{max_restarts}"
            )

            # Check if we've exceeded max restarts
            if len(restart_times) >= max_restarts:
                logger.error(
                    f"❌ WRAPPER - Maximum restart limit ({max_restarts}) reached in {restart_window} seconds. Waiting before retry..."
                )
                logger.error(
                    f"❌ WRAPPER - Restart times: {[time.strftime('%H:%M:%S', time.localtime(t)) for t in restart_times]}"
                )
                time.sleep(300)  # Wait 5 minutes before retrying
                restart_times = []  # Reset the counter
                restart_count = 0
                logger.info("🔄 WRAPPER - Restart counter reset, continuing...")
                continue

            # Run the Solace consumer
            exit_code = run_solace_consumer()

            if exit_code == 0:
                logger.info(
                    "✅ WRAPPER - Solace consumer exited normally (likely due to silence detection)"
                )
                logger.info("🔄 WRAPPER - Will restart consumer due to normal exit")
            else:
                logger.warning(
                    f"⚠️ WRAPPER - Solace consumer exited with code {exit_code}"
                )

        except KeyboardInterrupt:
            logger.info(
                "⚠️ WRAPPER - Keyboard interrupt received. Shutting down wrapper..."
            )
            break
        except Exception as e:
            logger.error(f"❌ WRAPPER - Unexpected error in wrapper: {e}")
            logger.error(f"❌ WRAPPER - Error type: {type(e).__name__}")

        # Increment restart count and record restart time
        restart_count += 1
        restart_times.append(time.time())

        # Wait before restarting
        wait_time = min(30, restart_count * 5)  # Exponential backoff, max 30 seconds
        logger.info(f"⏳ WRAPPER - Waiting {wait_time} seconds before restart...")
        logger.info(f"⏳ WRAPPER - Next restart attempt: {restart_count + 1}")
        time.sleep(wait_time)

    logger.info("Solace Consumer Wrapper shutting down")


if __name__ == "__main__":
    main()
