"""
Enhanced Solace Connection Manager - Based on FAA JMS Client patterns
Provides robust connection management, error handling, and monitoring
"""

import time
import threading
import uuid
import random
from typing import Optional, Callable, Dict, Any
from enum import Enum
from solace.messaging.messaging_service import (
    MessagingService,
    ReconnectionListener,
    ReconnectionAttemptListener,
    ServiceInterruptionListener,
    ServiceEvent,
)
from solace.messaging.config.retry_strategy import RetryStrategy
from solace.messaging.errors.pubsubplus_client_error import PubSubPlusClientError
from utils.logger import main_logger as logger


class ConnectionState(Enum):
    """Connection state enumeration"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class SolaceConnectionManager:
    """
    Enhanced connection manager based on FAA JMS Client patterns
    Provides robust connection management with proper error handling
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        vpn_name: str,
        client_name_prefix: str = "golfmike",
        max_retry_attempts: int = 10,
        retry_delay_base: float = 1.0,
        retry_delay_max: float = 60.0,
        keep_alive_interval: int = 30,
        connection_timeout: int = 30,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.vpn_name = vpn_name

        # Generate unique client name to prevent forced logout
        self.client_name = f"{client_name_prefix}_{uuid.uuid4().hex[:8]}"

        # Connection parameters
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay_base = retry_delay_base
        self.retry_delay_max = retry_delay_max
        self.keep_alive_interval = keep_alive_interval
        self.connection_timeout = connection_timeout

        # State management
        self.state = ConnectionState.DISCONNECTED
        self.messaging_service: Optional[MessagingService] = None
        self.retry_count = 0
        self.last_connection_time = None
        self.last_message_time = None
        self.connection_lock = threading.Lock()

        # Event callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None

        # Monitoring
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_monitoring = False

        logger.info(
            f"Initialized SolaceConnectionManager with client name: {self.client_name}"
        )

    def connect(self) -> bool:
        """
        Establish connection with retry logic and exponential backoff
        Based on FAA JMS Client connection patterns
        """
        with self.connection_lock:
            if self.state == ConnectionState.CONNECTED:
                logger.info("Already connected to Solace")
                return True

            self.state = ConnectionState.CONNECTING
            logger.info(f"Connecting to Solace: {self.host} (VPN: {self.vpn_name})")

            for attempt in range(self.max_retry_attempts):
                try:
                    # Create messaging service with SSL certificate validation disabled
                    # Using the correct property names from Solace Community
                    self.messaging_service = (
                        MessagingService.builder()
                        .from_properties(
                            {
                                "solace.messaging.transport.host": self.host,
                                "solace.messaging.service.vpn-name": self.vpn_name,
                                "solace.messaging.authentication.scheme.basic.username": self.username,
                                "solace.messaging.authentication.scheme.basic.password": self.password,
                                "solace.messaging.client-name": self.client_name,
                                # Disable SSL certificate validation using correct property names
                                "solace.messaging.tls.cert-validated": False,
                                "solace.messaging.tls.cert-validated-date": False,
                            }
                        )
                        .build()
                    )

                    # Set up event listeners
                    self._setup_event_listeners()

                    # Connect with timeout
                    self.messaging_service.connect()

                    self.state = ConnectionState.CONNECTED
                    self.retry_count = 0
                    self.last_connection_time = time.time()

                    logger.info(
                        f"Successfully connected to Solace (attempt {attempt + 1})"
                    )

                    # Start monitoring
                    self._start_monitoring()

                    # Notify callback
                    if self.on_connected:
                        self.on_connected()

                    return True

                except Exception as e:
                    self.retry_count += 1
                    logger.error(f"Connection attempt {attempt + 1} failed: {e}")

                    if attempt < self.max_retry_attempts - 1:
                        # Calculate exponential backoff with jitter
                        delay = min(
                            self.retry_delay_base * (2**attempt) + random.uniform(0, 1),
                            self.retry_delay_max,
                        )
                        logger.info(f"Retrying connection in {delay:.1f} seconds...")
                        time.sleep(delay)
                    else:
                        self.state = ConnectionState.FAILED
                        logger.error(
                            f"Failed to connect after {self.max_retry_attempts} attempts"
                        )
                        return False

            return False

    def disconnect(self):
        """Disconnect from Solace messaging service"""
        with self.connection_lock:
            if self.state == ConnectionState.DISCONNECTED:
                return

            logger.info("Disconnecting from Solace...")

            self._stop_monitoring()

            if self.messaging_service:
                try:
                    self.messaging_service.disconnect()
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")
                finally:
                    self.messaging_service = None

            self.state = ConnectionState.DISCONNECTED

            # Notify callback
            if self.on_disconnected:
                self.on_disconnected()

            logger.info("Disconnected from Solace")

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return (
            self.state == ConnectionState.CONNECTED
            and self.messaging_service is not None
        )

    def get_messaging_service(self) -> Optional[MessagingService]:
        """Get the messaging service instance"""
        return self.messaging_service if self.is_connected() else None

    def _setup_event_listeners(self):
        """Set up Solace event listeners for connection monitoring"""
        if not self.messaging_service:
            return

        # Reconnection listener
        class ReconnectionListenerImpl(ReconnectionListener):
            def on_reconnected(self, e: ServiceEvent):
                logger.info("Successfully reconnected to Solace")
                self.state = ConnectionState.CONNECTED
                self.retry_count = 0
                self.last_connection_time = time.time()

            def on_reconnecting(self, e: ServiceEvent):
                logger.warning("Reconnecting to Solace...")
                self.state = ConnectionState.RECONNECTING

        # Reconnection attempt listener
        class ReconnectionAttemptListenerImpl(ReconnectionAttemptListener):
            def on_reconnection_attempt(self, e: ServiceEvent):
                logger.info(f"Reconnection attempt {self.retry_count + 1}")

            def on_reconnecting(self, e: ServiceEvent):
                logger.info("Reconnection attempt listener - reconnecting")

        # Service interruption listener
        class ServiceInterruptionListenerImpl(ServiceInterruptionListener):
            def on_service_interrupted(self, e: ServiceEvent):
                logger.warning("Solace service interrupted")
                self.state = ConnectionState.DISCONNECTED

            def on_service_interruption_cleared(self, e: ServiceEvent):
                logger.info("Solace service interruption cleared")

        # Add listeners
        self.messaging_service.add_reconnection_listener(ReconnectionListenerImpl())
        self.messaging_service.add_reconnection_attempt_listener(
            ReconnectionAttemptListenerImpl()
        )
        self.messaging_service.add_service_interruption_listener(
            ServiceInterruptionListenerImpl()
        )

    def _start_monitoring(self):
        """Start connection monitoring thread"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Connection monitoring started")

    def _stop_monitoring(self):
        """Stop connection monitoring thread"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Connection monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop for connection health"""
        while self.is_monitoring:
            try:
                time.sleep(self.keep_alive_interval)

                if not self.is_monitoring:
                    break

                # Check connection health
                if self.state == ConnectionState.CONNECTED:
                    # Update last message time if we have a callback
                    if self.on_message_received:
                        self.last_message_time = time.time()

                    # Check for stale connection (no messages for extended period)
                    if self.last_message_time:
                        time_since_last_message = time.time() - self.last_message_time
                        if time_since_last_message > 300:  # 5 minutes
                            logger.warning(
                                f"No messages received for {time_since_last_message:.0f} seconds"
                            )

                elif self.state in [
                    ConnectionState.DISCONNECTED,
                    ConnectionState.FAILED,
                ]:
                    # Attempt reconnection
                    logger.info("Attempting to reconnect...")
                    self.connect()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    def update_message_timestamp(self):
        """Update the last message received timestamp"""
        self.last_message_time = time.time()

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "state": self.state.value,
            "client_name": self.client_name,
            "retry_count": self.retry_count,
            "last_connection_time": self.last_connection_time,
            "last_message_time": self.last_message_time,
            "is_connected": self.is_connected(),
            "uptime": (
                time.time() - self.last_connection_time
                if self.last_connection_time
                else 0
            ),
        }
