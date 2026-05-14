"""
Enhanced Traffic Consumer - Based on FAA JMS Client patterns
Provides robust connection management and high-performance message processing
"""

import time
import sys
import os
import signal
from utils.logger import main_logger as logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consumers.solace_connection_manager import SolaceConnectionManager
from consumers.solace_message_processor import SolaceMessageProcessor
from swim_data_processor import parse_and_store_to_database

# Solace message broker connection parameters
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "TFMS"
QUEUE_NAME = "gear.twinhawk.co.TFMS.39cf9ef5-e72e-4d5c-bd12-f700b6b725c3.OUT"

# Global instances
connection_manager: SolaceConnectionManager = None
message_processor: SolaceMessageProcessor = None


def process_traffic_message(message_data):
    """Process traffic message and store to database"""
    try:
        # Update connection monitor timestamp
        if connection_manager:
            connection_manager.update_message_timestamp()

        payload = message_data.get("payload")
        if not payload:
            logger.warning("No payload in message data")
            return

        # Process and store the message (reduced logging for performance)
        logger.debug(f"Processing traffic message: {len(payload)} bytes from {message_data.get('destination', 'Unknown')}")
        parse_and_store_to_database(payload)

    except Exception as e:
        logger.error(f"❌ Error processing traffic message: {e}", exc_info=True)


def on_connected():
    """Callback when connected to Solace"""
    logger.info("🔗 Traffic Consumer connected to Solace")

    # Start message processor
    global message_processor
    if message_processor and connection_manager:
        messaging_service = connection_manager.get_messaging_service()
        if messaging_service:
            message_processor.start(messaging_service, QUEUE_NAME)


def on_disconnected():
    """Callback when disconnected from Solace"""
    logger.warning("🔌 Traffic Consumer disconnected from Solace")

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
    logger.info("Shutting down Traffic Consumer...")

    global message_processor, connection_manager

    # Stop message processor
    if message_processor:
        message_processor.stop()
        message_processor = None

    # Disconnect from Solace
    if connection_manager:
        connection_manager.disconnect()
        connection_manager = None

    logger.info("Traffic Consumer shutdown complete")


def run():
    """Main function to run the enhanced traffic consumer"""
    global connection_manager, message_processor

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("🚀 Starting Enhanced Traffic Consumer...")
        logger.info(f"📡 Connecting to: {HOST}")
        logger.info(f"🏢 VPN: {VPN_NAME}")
        logger.info(f"📬 Queue: {QUEUE_NAME}")

        # Create connection manager with enhanced configuration
        connection_manager = SolaceConnectionManager(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            vpn_name=VPN_NAME,
            client_name_prefix="traffic_consumer",
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
        # Increased queue size and processors to handle high message volume
        message_processor = SolaceMessageProcessor(
            concurrent_consumer_count=4,  # Multiple consumers for concurrent message consumption
            parallel_processor_count=8,  # Increased parallel processing threads for better throughput
            processing_queue_size=50000,  # Increased queue size to handle large message bursts
            message_handler=process_traffic_message,
        )

        # Connect to Solace
        if connection_manager.connect():
            logger.info("✅ Traffic Consumer started successfully")

            # Keep running until shutdown
            try:
                while True:
                    time.sleep(1)

                    # Log stats periodically and check queue health
                    if connection_manager and message_processor:
                        stats = message_processor.get_stats()
                        queue_size = stats.get("queue_size", 0)
                        is_consuming = stats.get("is_consuming", True)
                        
                        # Log every 100 messages or if queue is getting full
                        if (
                            stats["messages_processed"] > 0
                            and (stats["messages_processed"] % 100 == 0 or queue_size > 10000)
                        ):
                            status_icon = "✅" if is_consuming else "⚠️"
                            logger.info(
                                f"📊 {status_icon} Processed {stats['messages_processed']} messages, "
                                f"Queue: {queue_size}/{stats.get('processing_queue_size', 50000)}, "
                                f"Rate: {stats.get('messages_per_second', 0):.1f} msg/s, "
                                f"Consuming: {is_consuming}"
                            )
                        
                        # Warn if queue is getting very full
                        if queue_size > 40000:
                            logger.warning(
                                f"⚠️ Queue is {queue_size} messages (80% full). "
                                f"Consider increasing parallel_processor_count or optimizing processing."
                            )

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
        else:
            logger.error("❌ Failed to connect to Solace")
            return 1

    except Exception as e:
        logger.error(f"❌ Error starting Traffic Consumer: {e}", exc_info=True)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
