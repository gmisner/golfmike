"""
TBFM Consumer — FAA SWIM Metering Publication (TBFM VPN)

Connects to the TBFM VPN on ems2.swim.faa.gov and processes metering
publications: arrival sequences, meter-fix times, delays, and TMI data.

Credentials are read from environment variables; never hardcode them.
"""

import os
import sys
import time
import signal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import main_logger as logger
from consumers.solace_connection_manager import SolaceConnectionManager
from consumers.solace_message_processor import SolaceMessageProcessor
from parsers.tbfm_parser import TBFMParser
from storers.tbfm_storer import TBFMStorer

HOST       = os.getenv("SWIM_HOST",     "tcps://ems2.swim.faa.gov:55443")
USERNAME   = os.getenv("SWIM_USERNAME", "gear.twinhawk.co")
PASSWORD   = os.getenv("SWIM_PASSWORD", "")
VPN_NAME   = os.getenv("TBFM_VPN",     "TBFM")
QUEUE_NAME = os.getenv("TBFM_QUEUE",   "gear.twinhawk.co.TBFM.73a8d366-e856-4085-a58a-fa7ec3214bd1.OUT")

connection_manager: SolaceConnectionManager = None
message_processor:  SolaceMessageProcessor  = None

_parser = TBFMParser()
_storer = TBFMStorer()


def process_tbfm_message(message_data: dict) -> None:
    """Parse a TBFM XML publication and persist it."""
    try:
        if connection_manager:
            connection_manager.update_message_timestamp()

        payload = message_data.get("payload")
        if not payload:
            logger.warning("TBFM: empty payload, skipping")
            return

        logger.debug("TBFM message: %d bytes from %s",
                     len(payload), message_data.get("destination", "?"))

        records = _parser.parse(payload)
        if records:
            stored = _storer.store(records)
            logger.debug("TBFM: stored %d records", stored)

    except Exception as exc:
        logger.error("TBFM message processing error: %s", exc, exc_info=True)


def on_connected() -> None:
    logger.info("TBFM Consumer connected to Solace VPN=%s", VPN_NAME)
    global message_processor
    if message_processor and connection_manager:
        svc = connection_manager.get_messaging_service()
        if svc:
            message_processor.start(svc, QUEUE_NAME)


def on_disconnected() -> None:
    logger.warning("TBFM Consumer disconnected from Solace")
    global message_processor
    if message_processor:
        message_processor.stop()


def on_message_received() -> None:
    if connection_manager:
        connection_manager.update_message_timestamp()


def signal_handler(signum, frame):
    logger.info("TBFM Consumer shutting down (signal %s)...", signum)
    shutdown()


def shutdown():
    global connection_manager, message_processor
    if message_processor:
        message_processor.stop()
        message_processor = None
    if connection_manager:
        connection_manager.disconnect()
        connection_manager = None
    logger.info("TBFM Consumer shutdown complete")


def run():
    global connection_manager, message_processor

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT,  signal_handler)

    try:
        logger.info("Starting TBFM Consumer...")
        logger.info(f"Connecting to: {HOST}")
        logger.info(f"VPN: {VPN_NAME}")
        logger.info(f"Queue: {QUEUE_NAME}")

        connection_manager = SolaceConnectionManager(
            host=HOST,
            username=USERNAME,
            password=PASSWORD,
            vpn_name=VPN_NAME,
            client_name_prefix="tbfm_consumer",
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
            concurrent_consumer_count=2,
            parallel_processor_count=4,
            processing_queue_size=10000,
            message_handler=process_tbfm_message,
        )

        if connection_manager.connect():
            logger.info("TBFM Consumer started successfully")
            try:
                while True:
                    time.sleep(1)
                    if connection_manager and message_processor:
                        stats = message_processor.get_stats()
                        if stats["messages_processed"] > 0 and stats["messages_processed"] % 50 == 0:
                            logger.info(
                                "TBFM: processed %d messages, queue: %d, %.1f msg/s",
                                stats["messages_processed"],
                                stats.get("queue_size", 0),
                                stats.get("messages_per_second", 0),
                            )
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
        else:
            logger.error("Failed to connect to Solace (TBFM consumer)")
            return 1

    except Exception as exc:
        logger.error("Error starting TBFM Consumer: %s", exc, exc_info=True)
        return 1
    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(run())
