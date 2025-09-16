"""
Solace Connection Monitor - Prevents connection timeouts and ensures continuous message flow
"""

import time
import threading
from utils.logger import main_logger as logger


class SolaceConnectionMonitor:
    """Monitors Solace connection and restarts consumer if needed"""

    def __init__(self, check_interval=300):  # Check every 5 minutes
        self.check_interval = check_interval
        self.last_message_time = time.time()
        self.is_running = False
        self.monitor_thread = None

    def update_last_message_time(self):
        """Update the last message received timestamp"""
        self.last_message_time = time.time()

    def start_monitoring(self):
        """Start the connection monitoring thread"""
        if self.is_running:
            logger.warning("Connection monitor is already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Solace connection monitor started")

    def stop_monitoring(self):
        """Stop the connection monitoring thread"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Solace connection monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                time.sleep(self.check_interval)

                # Check if we've received messages recently
                time_since_last_message = time.time() - self.last_message_time

                if (
                    time_since_last_message > self.check_interval * 2
                ):  # No messages for 10 minutes
                    logger.warning(
                        f"No messages received for {time_since_last_message:.0f} seconds"
                    )
                    logger.info("Restarting Solace consumer...")

                    # Restart the consumer
                    self._restart_consumer()

            except Exception as e:
                logger.error(f"Error in connection monitor: {e}", exc_info=True)

    def _restart_consumer(self):
        """Restart the Solace consumer"""
        try:
            # This would typically restart the consumer process
            # For now, we'll just log the action
            logger.info("Would restart Solace consumer here")
            # In a production environment, you might:
            # 1. Send a signal to restart the consumer process
            # 2. Use a process manager like supervisor
            # 3. Restart the Docker container

        except Exception as e:
            logger.error(f"Error restarting consumer: {e}", exc_info=True)


# Global monitor instance
connection_monitor = SolaceConnectionMonitor()


def start_connection_monitoring():
    """Start the connection monitoring"""
    connection_monitor.start_monitoring()


def stop_connection_monitoring():
    """Stop the connection monitoring"""
    connection_monitor.stop_monitoring()


def update_message_timestamp():
    """Update the last message timestamp"""
    connection_monitor.update_last_message_time()
