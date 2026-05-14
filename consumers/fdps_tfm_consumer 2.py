"""
FDPS TFM consumer — Solace queue for TFMData / flight-data style messages on VPN FDPS.

Uses the same parse → store pipeline as the traffic consumer (msgType via //@msgType).
"""

import time
import sys
import os
import signal

from utils.logger import main_logger as logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consumers.solace_connection_manager import SolaceConnectionManager
from consumers.solace_message_processor import SolaceMessageProcessor
from swim_data_processor import parse_and_store_to_database

HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "FDPS"
QUEUE_NAME = "gear.twinhawk.co.FDPS.4de2dd99-fd7d-4246-9460-8c32dfdcfede.OUT"

connection_manager: SolaceConnectionManager = None
message_processor: SolaceMessageProcessor = None


def process_fdps_tfm_message(message_data):
    """Parse TFM XML from FDPS queue and store using registered parsers/storers."""
    try:
        if connection_manager:
            connection_manager.update_message_timestamp()

        payload = message_data.get("payload")
        if not payload:
            logger.warning("No payload in message data")
            return

        logger.debug(
            "FDPS TFM message: %s bytes from %s",
            len(payload),
            message_data.get("destination", "Unknown"),
        )
        parse_and_store_to_database(payload)

    except Exception as e:
        logger.error(f"Error processing FDPS TFM message: {e}", exc_info=True)


def on_connected():
    logger.info("FDPS TFM consumer connected to Solace")
    global message_processor
    if message_processor and connection_manager:
        messaging_service = connection_manager.get_messaging_service()
        if messaging_service:
            message_processor.start(messaging_service, QUEUE_NAME)


def on_disconnected():
    logger.warning("FDPS TFM consumer disconnected from Solace")
    global message_processor
    if message_processor:
        message_processor.stop()


def on_message_received():
    if connection_manager:
        connection_manager.update_message_timestamp()


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown()


def shutdown():
    logger.info("Shutting down FDPS TFM consumer...")
    global message_processor, connection_manager
    if message_processor:
        message_processor.stop()
        message_processor = None
    if connection_manager:
        connection_manager.disconnect()
        connection_manager = None
    logger.info("FDPS TFM consumer shutdown complete")


def run():
    global connection_manager, message_processor

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting FDPS TFM consumer...")
        logger.info(f"Connecting to: {HOST}")
        logger.info(f"VPN: {VPN_NAME}")
        logger.info(f"Queue: {QUEUE_NAME}")

        connection_manager = SolaceConnectionManager(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            vpn_name=VPN_NAME,
            client_name_prefix="fdps_tfm_consumer",
            max_retry_attempts=10,
            retry_delay_base=1.0,
            retry_delay_max=60.0,
            keep_alive_interval=30,
            connection_timeout=30,
        )

        connection_manager.on_connected = on_connected
        connection_manager.on_disconnected = on_disconnected
        connection_manager.on_message_received = on_message_received

        message_processor = SolaceMessageProcessor(
            concurrent_consumer_count=4,
            parallel_processor_count=8,
            processing_queue_size=50000,
            message_handler=process_fdps_tfm_message,
        )

        if connection_manager.connect():
            logger.info("FDPS TFM consumer started successfully")
            try:
                while True:
                    time.sleep(1)
                    if connection_manager and message_processor:
                        stats = message_processor.get_stats()
                        queue_size = stats.get("queue_size", 0)
                        is_consuming = stats.get("is_consuming", True)
                        if stats["messages_processed"] > 0 and (
                            stats["messages_processed"] % 100 == 0 or queue_size > 10000
                        ):
                            status_icon = "✅" if is_consuming else "⚠️"
                            logger.info(
                                f"{status_icon} FDPS TFM: processed "
                                f"{stats['messages_processed']} messages, "
                                f"queue: {queue_size}/"
                                f"{stats.get('processing_queue_size', 50000)}, "
                                f"{stats.get('messages_per_second', 0):.1f} msg/s"
                            )
                        if queue_size > 40000:
                            logger.warning(
                                "FDPS TFM internal queue is very full (%s); "
                                "consider scaling workers",
                                queue_size,
                            )
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
        else:
            logger.error("Failed to connect to Solace (FDPS TFM consumer)")
            return 1

    except Exception as e:
        logger.error(f"Error starting FDPS TFM consumer: {e}", exc_info=True)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(run())
