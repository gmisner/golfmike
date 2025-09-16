"""
Enhanced Flight Plan Consumer - Based on FAA JMS Client patterns
Provides robust connection management and high-performance message processing
"""

import time
import sys
import os
import signal
from utils.logger import main_logger as logger
from celery_app import app as celery_app

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consumers.solace_connection_manager import SolaceConnectionManager
from consumers.solace_message_processor import SolaceMessageProcessor

# Solace message broker connection parameters for Flight Plan data
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "FDPS"  # Flight Data Processing System
QUEUE_NAME = "gear.twinhawk.co.FDPS.e2291164-1090-45e0-981c-80ae9d75e77e.OUT"

# Global instances
connection_manager: SolaceConnectionManager = None
message_processor: SolaceMessageProcessor = None


def process_flight_plan_message(message_data):
    """Process flight plan message and dispatch to Celery task"""
    try:
        # Update connection monitor timestamp
        if connection_manager:
            connection_manager.update_message_timestamp()

        payload = message_data.get("payload")
        if not payload:
            logger.warning("No payload in message data")
            return

        logger.info("🔄 PROCESSING FLIGHT PLAN MESSAGE - Starting message processing")
        logger.info(f"📋 Payload Size: {len(payload)} bytes")
        logger.info(f"📋 Destination: {message_data.get('destination', 'Unknown')}")

        # Dispatch to Celery task for processing
        task_result = celery_app.send_task(
            "tasks.process_flight_plan_xml", args=[payload]
        )
        logger.info(
            f"✅ Celery task {task_result.id} started for processing flight plan message."
        )

    except Exception as e:
        logger.error(f"❌ Error processing flight plan message: {e}", exc_info=True)


def on_connected():
    """Callback when connected to Solace"""
    logger.info("🔗 Flight Plan Consumer connected to Solace")

    # Start message processor
    global message_processor
    if message_processor and connection_manager:
        messaging_service = connection_manager.get_messaging_service()
        if messaging_service:
            message_processor.start(messaging_service, QUEUE_NAME)


def on_disconnected():
    """Callback when disconnected from Solace"""
    logger.warning("🔌 Flight Plan Consumer disconnected from Solace")

    # Stop message processor
    global message_processor
    if message_processor:
        message_processor.stop()


def on_message_received():
    """Callback when message is received"""
    if connection_manager:
        connection_manager.update_message_timestamp()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown()


def shutdown():
    """Graceful shutdown of the consumer"""
    logger.info("Shutting down Flight Plan Consumer...")

    global message_processor, connection_manager

    # Stop message processor
    if message_processor:
        message_processor.stop()
        message_processor = None

    # Disconnect from Solace
    if connection_manager:
        connection_manager.disconnect()
        connection_manager = None

    logger.info("Flight Plan Consumer shutdown complete")


def run():
    """Main function to run the enhanced flight plan consumer"""
    global connection_manager, message_processor

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("🚀 Starting Enhanced Flight Plan Consumer...")
        logger.info(f"📡 Connecting to: {HOST}")
        logger.info(f"🏢 VPN: {VPN_NAME}")
        logger.info(f"📬 Queue: {QUEUE_NAME}")

        # Create connection manager with enhanced configuration
        connection_manager = SolaceConnectionManager(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            vpn_name=VPN_NAME,
            client_name_prefix="flight_plan_consumer",
            max_retry_attempts=10,
            retry_delay_base=1.0,
            retry_delay_max=60.0,
            keep_alive_interval=30,
            connection_timeout=30,
        )

        # Set up callbacks
        connection_manager.on_connected = on_connected
        connection_manager.on_disconnected = on_disconnected
        connection_manager.on_message_received = on_message_received

        # Create message processor with high-performance configuration
        message_processor = SolaceMessageProcessor(
            concurrent_consumer_count=4,  # Multiple consumers for concurrent message consumption
            parallel_processor_count=2,  # Parallel processing threads
            processing_queue_size=10000,  # Large queue to handle message bursts
            message_handler=process_flight_plan_message,
        )

        # Connect to Solace
        if connection_manager.connect():
            logger.info("✅ Flight Plan Consumer started successfully")

            # Keep running until shutdown
            try:
                while True:
                    time.sleep(1)

                    # Log stats periodically
                    if connection_manager and message_processor:
                        stats = message_processor.get_stats()
                        if (
                            stats["messages_processed"] > 0
                            and stats["messages_processed"] % 100 == 0
                        ):
                            logger.info(
                                f"📊 Processed {stats['messages_processed']} messages, "
                                f"Queue: {stats['queue_size']}, "
                                f"Rate: {stats['messages_per_second']:.1f} msg/s"
                            )

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
        else:
            logger.error("❌ Failed to connect to Solace")
            return 1

    except Exception as e:
        logger.error(f"❌ Error starting Flight Plan Consumer: {e}", exc_info=True)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
