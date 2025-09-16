"""
Enhanced Solace Monitoring - Based on FAA JMS Client patterns
Provides comprehensive monitoring and health checks for all consumers
"""

import time
import json
import threading
from typing import Dict, List, Any
from utils.logger import main_logger as logger


class SolaceMonitor:
    """
    Comprehensive monitoring system for all Solace consumers
    Based on FAA JMS Client monitoring patterns
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.is_running = False
        self.monitor_thread = None
        self.consumers = {}  # Track consumer instances
        self.alert_thresholds = {
            "max_queue_size": 8000,  # 80% of 10k queue
            "min_processing_rate": 0.1,  # messages per second
            "max_connection_retries": 5,
            "max_uptime_without_messages": 300,  # 5 minutes
        }

    def register_consumer(self, name: str, connection_manager, message_processor):
        """Register a consumer for monitoring"""
        self.consumers[name] = {
            "connection_manager": connection_manager,
            "message_processor": message_processor,
            "last_health_check": time.time(),
            "alerts": [],
        }
        logger.info(f"Registered consumer for monitoring: {name}")

    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_running:
            logger.warning("Monitor is already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Solace monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Solace monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                time.sleep(self.check_interval)

                if not self.is_running:
                    break

                # Check health of all registered consumers
                for name, consumer_data in self.consumers.items():
                    self._check_consumer_health(name, consumer_data)

                # Log overall system status
                self._log_system_status()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    def _check_consumer_health(self, name: str, consumer_data: Dict[str, Any]):
        """Check health of a specific consumer"""
        try:
            connection_manager = consumer_data["connection_manager"]
            message_processor = consumer_data["message_processor"]

            # Get connection stats
            conn_stats = (
                connection_manager.get_connection_stats() if connection_manager else {}
            )
            proc_stats = message_processor.get_stats() if message_processor else {}

            # Check for alerts
            alerts = []

            # Check connection state
            if conn_stats.get("state") != "connected":
                alerts.append(f"Connection state: {conn_stats.get('state', 'unknown')}")

            # Check retry count
            if (
                conn_stats.get("retry_count", 0)
                > self.alert_thresholds["max_connection_retries"]
            ):
                alerts.append(f"High retry count: {conn_stats.get('retry_count', 0)}")

            # Check queue size
            queue_size = proc_stats.get("queue_size", 0)
            if queue_size > self.alert_thresholds["max_queue_size"]:
                alerts.append(f"Queue size high: {queue_size}")

            # Check processing rate
            processing_rate = proc_stats.get("messages_per_second", 0)
            if (
                processing_rate < self.alert_thresholds["min_processing_rate"]
                and proc_stats.get("uptime", 0) > 60
            ):
                alerts.append(f"Low processing rate: {processing_rate:.2f} msg/s")

            # Check for stale connection (no messages for extended period)
            last_message_time = conn_stats.get("last_message_time")
            if last_message_time:
                time_since_last_message = time.time() - last_message_time
                if (
                    time_since_last_message
                    > self.alert_thresholds["max_uptime_without_messages"]
                ):
                    alerts.append(
                        f"No messages for {time_since_last_message:.0f} seconds"
                    )

            # Update consumer data
            consumer_data["last_health_check"] = time.time()
            consumer_data["alerts"] = alerts

            # Log alerts
            if alerts:
                logger.warning(f"🚨 {name} alerts: {'; '.join(alerts)}")

        except Exception as e:
            logger.error(f"Error checking health for {name}: {e}", exc_info=True)

    def _log_system_status(self):
        """Log overall system status"""
        try:
            total_consumers = len(self.consumers)
            connected_consumers = 0
            total_messages_processed = 0
            total_queue_size = 0

            for name, consumer_data in self.consumers.items():
                connection_manager = consumer_data["connection_manager"]
                message_processor = consumer_data["message_processor"]

                if connection_manager and connection_manager.is_connected():
                    connected_consumers += 1

                if message_processor:
                    stats = message_processor.get_stats()
                    total_messages_processed += stats.get("messages_processed", 0)
                    total_queue_size += stats.get("queue_size", 0)

            logger.info(
                f"📊 System Status: {connected_consumers}/{total_consumers} consumers connected, "
                f"{total_messages_processed} total messages processed, "
                f"{total_queue_size} total queue size"
            )

        except Exception as e:
            logger.error(f"Error logging system status: {e}", exc_info=True)

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information"""
        health_data = {
            "timestamp": time.time(),
            "consumers": {},
            "overall_status": "healthy",
        }

        try:
            total_alerts = 0

            for name, consumer_data in self.consumers.items():
                connection_manager = consumer_data["connection_manager"]
                message_processor = consumer_data["message_processor"]

                conn_stats = (
                    connection_manager.get_connection_stats()
                    if connection_manager
                    else {}
                )
                proc_stats = message_processor.get_stats() if message_processor else {}

                consumer_health = {
                    "connection_stats": conn_stats,
                    "processing_stats": proc_stats,
                    "alerts": consumer_data.get("alerts", []),
                    "last_health_check": consumer_data.get("last_health_check", 0),
                }

                health_data["consumers"][name] = consumer_health
                total_alerts += len(consumer_data.get("alerts", []))

            # Determine overall status
            if total_alerts > 0:
                health_data["overall_status"] = (
                    "degraded" if total_alerts < 5 else "critical"
                )

        except Exception as e:
            logger.error(f"Error getting system health: {e}", exc_info=True)
            health_data["overall_status"] = "error"

        return health_data

    def export_health_report(self, filename: str = None):
        """Export health report to JSON file"""
        if not filename:
            filename = f"solace_health_report_{int(time.time())}.json"

        try:
            health_data = self.get_system_health()

            with open(filename, "w") as f:
                json.dump(health_data, f, indent=2, default=str)

            logger.info(f"Health report exported to {filename}")

        except Exception as e:
            logger.error(f"Error exporting health report: {e}", exc_info=True)


# Global monitor instance
solace_monitor = SolaceMonitor()


def register_consumer(name: str, connection_manager, message_processor):
    """Register a consumer for monitoring"""
    solace_monitor.register_consumer(name, connection_manager, message_processor)


def start_monitoring():
    """Start the monitoring system"""
    solace_monitor.start_monitoring()


def stop_monitoring():
    """Stop the monitoring system"""
    solace_monitor.stop_monitoring()


def get_system_health():
    """Get system health information"""
    return solace_monitor.get_system_health()


def export_health_report(filename: str = None):
    """Export health report"""
    solace_monitor.export_health_report(filename)
