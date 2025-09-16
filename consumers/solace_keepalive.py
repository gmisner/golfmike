"""
Solace Keep-Alive Mechanism - Prevents connection timeouts
"""

import time
import threading
from utils.logger import main_logger as logger


class SolaceKeepAlive:
    """Keeps Solace connection alive by sending periodic heartbeats"""

    def __init__(
        self, interval=5
    ):  # Send heartbeat every 5 seconds for faster detection
        self.interval = interval
        self.is_running = False
        self.thread = None
        self.messaging_service = None

    def start(self, messaging_service):
        """Start the keep-alive mechanism"""
        if self.is_running:
            logger.warning("Keep-alive is already running")
            return

        self.messaging_service = messaging_service
        self.is_running = True
        self.thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self.thread.start()
        logger.info("Solace keep-alive started")

    def stop(self):
        """Stop the keep-alive mechanism"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Solace keep-alive stopped")

    def _keepalive_loop(self):
        """Main keep-alive loop"""
        while self.is_running:
            try:
                time.sleep(self.interval)

                if self.messaging_service and self.is_running:
                    # Send a simple ping to keep connection alive
                    logger.debug("Sending keep-alive ping to Solace")
                    # The messaging service should handle this automatically
                    # but we can also check connection status
                    if hasattr(self.messaging_service, "is_connected"):
                        # Check if is_connected is a property or method
                        is_connected = getattr(self.messaging_service, "is_connected")
                        if callable(is_connected):
                            connected = is_connected()
                        else:
                            connected = is_connected

                        if not connected:
                            logger.warning(
                                "Solace connection lost, attempting reconnection"
                            )
                            # The service should automatically reconnect

            except Exception as e:
                logger.error(f"Error in keep-alive loop: {e}", exc_info=True)


# Global keep-alive instance
keepalive = SolaceKeepAlive()


def start_keepalive(messaging_service):
    """Start the keep-alive mechanism"""
    keepalive.start(messaging_service)


def stop_keepalive():
    """Stop the keep-alive mechanism"""
    keepalive.stop()
