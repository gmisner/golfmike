"""
Enhanced Weather Consumer - Based on FAA JMS Client patterns
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
from parsers.weather_parser import WeatherXMLParser
from storers.weather_storer import WeatherDataStorer

# Solace message broker connection parameters
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "ITWS"
QUEUE_NAME = "gear.twinhawk.co.ITWS.35078235-3acd-40a5-931f-f9e15c04f7da.OUT"

# Global instances
connection_manager: SolaceConnectionManager = None
message_processor: SolaceMessageProcessor = None

# Initialize weather processing components
weather_parser = WeatherXMLParser()
weather_storer = WeatherDataStorer()


def process_weather_message(message_data):
    """Process weather message and store to database"""
    try:
        # Update connection monitor timestamp
        if connection_manager:
            connection_manager.update_message_timestamp()

        payload = message_data.get("payload")
        if not payload:
            logger.warning("No payload in message data")
            return

        logger.info("🔄 PROCESSING WEATHER MESSAGE - Starting message processing")
        logger.info(f"📋 Payload Size: {len(payload)} bytes")
        logger.info(f"📋 Destination: {message_data.get('destination', 'Unknown')}")

        # Parse and store weather data
        weather_data = weather_parser.parse_message(payload)
        if weather_data:
            stored = weather_storer.store_weather_data(weather_data)
            if stored:
                logger.info("✅ Weather data stored successfully")
            else:
                logger.warning("Weather message parsed but storage did not complete")
        else:
            logger.warning("No weather data extracted from message")

    except Exception as e:
        logger.error(f"❌ Error processing weather message: {e}", exc_info=True)


def on_connected():
    """Callback when connected to Solace"""
    logger.info("🔗 Weather Consumer connected to Solace")

    # Start message processor
    global message_processor
    if message_processor and connection_manager:
        messaging_service = connection_manager.get_messaging_service()
        if messaging_service:
            message_processor.start(messaging_service, QUEUE_NAME)


def on_disconnected():
    """Callback when disconnected from Solace"""
    logger.warning("🔌 Weather Consumer disconnected from Solace")

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
    logger.info("Shutting down Weather Consumer...")

    global message_processor, connection_manager

    # Stop message processor
    if message_processor:
        message_processor.stop()
        message_processor = None

    # Disconnect from Solace
    if connection_manager:
        connection_manager.disconnect()
        connection_manager = None

    logger.info("Weather Consumer shutdown complete")


def run():
    """Main function to run the enhanced weather consumer"""
    global connection_manager, message_processor

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("🚀 Starting Enhanced Weather Consumer...")
        logger.info(f"📡 Connecting to: {HOST}")
        logger.info(f"🏢 VPN: {VPN_NAME}")
        logger.info(f"📬 Queue: {QUEUE_NAME}")

        # Create connection manager with enhanced configuration
        connection_manager = SolaceConnectionManager(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            vpn_name=VPN_NAME,
            client_name_prefix="weather_consumer",
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
            parallel_processor_count=3,  # More parallel processing threads
            processing_queue_size=10000,  # Large queue to handle message bursts
            message_handler=process_weather_message,
        )

        # Connect to Solace
        if connection_manager.connect():
            logger.info("✅ Weather Consumer started successfully")

            # Keep running until shutdown
            try:
                while True:
                    time.sleep(1)

                    # Log stats periodically
                    if connection_manager and message_processor:
                        stats = message_processor.get_stats()
                        if (
                            stats["messages_processed"] > 0
                            and stats["messages_processed"] % 50 == 0
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
        logger.error(f"❌ Error starting Weather Consumer: {e}", exc_info=True)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
