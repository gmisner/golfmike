# gm_tfms_sub.py
import time
from solace.messaging.messaging_service import (
    MessagingService,
    ReconnectionListener,
    ReconnectionAttemptListener,
    ServiceInterruptionListener,
    ServiceEvent,
)
from solace.messaging.resources.queue import Queue
from solace.messaging.config.retry_strategy import RetryStrategy
from solace.messaging.receiver.persistent_message_receiver import (
    PersistentMessageReceiver,
)
from solace.messaging.receiver.message_receiver import MessageHandler, InboundMessage
from solace.messaging.errors.pubsubplus_client_error import PubSubPlusClientError
from solace.messaging.config.missing_resources_creation_configuration import (
    MissingResourcesCreationStrategy,
)
from swim_data_processor import parse_and_store_to_database
from utils.logger import main_logger as logger

# Solace message broker connection parameters
HOST = "tcps://ems1.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "TFMS"
QUEUE_NAME = "gear.twinhawk.co.TFMS.b70b3338-3b0e-4388-bba0-b49d870a502c.OUT"

# Delay between processing messages (in seconds)
PROCESSING_DELAY = 5  # Adjust this value as needed


class MessageHandlerImpl(MessageHandler):
    def __init__(self, persistent_receiver: PersistentMessageReceiver):
        self.receiver: PersistentMessageReceiver = persistent_receiver

    def on_message(self, message: InboundMessage):
        payload = (
            message.get_payload_as_string()
            if message.get_payload_as_string() is not None
            else message.get_payload_as_bytes()
        )
        if isinstance(payload, bytearray):
            logger.info(
                f"Received a message of type: {type(payload)}. Decoding to string"
            )
            payload = payload.decode()

        # LOG THE RECEIVED XML HERE (outside the conditional block):
        logger.info(f"Received XML: {payload}")

        try:
            parsed_data = parse_and_store_to_database(payload)
            if parsed_data:
                logger.info(f"Stored data for flight: {parsed_data.aircraftId}")
            else:
                logger.error("Failed to parse and store the XML data")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

        # Add a delay to avoid hitting rate limits
        time.sleep(PROCESSING_DELAY)


# Inner classes for error handling
class ServiceEventHandler(
    ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener
):
    def on_reconnected(self, e: ServiceEvent):
        logger.info("Reconnected to the service")
        logger.info(f"Error cause: {e.get_cause()}")
        logger.info(f"Message: {e.get_message()}")

    def on_reconnecting(self, e: "ServiceEvent"):
        logger.info("Attempting to reconnect to the service")
        logger.info(f"Error cause: {e.get_cause()}")
        logger.info(f"Message: {e.get_message()}")

    def on_service_interrupted(self, e: "ServiceEvent"):
        logger.warning("Service interrupted")
        logger.warning(f"Error cause: {e.get_cause()}")
        logger.warning(f"Message: {e.get_message()}")


# Broker Config. Note: Could pass other properties Look into
broker_props = {
    "solace.messaging.transport.host": HOST,
    "solace.messaging.service.vpn-name": VPN_NAME,
    "solace.messaging.authentication.scheme.basic.username": USERNAME,
    "solace.messaging.authentication.scheme.basic.password": PASSWORD,
    "solace.messaging.transport.security.trust-store": "/GolfMike/FAA.jks",
    "solace.messaging.transport.security.trust-store-password": "faa.4TW!",
    "solace.messaging.tls.cert-validated": False,
    "solace.messaging.tls.cert-validated-date": False,
}

# Build A messaging service with a reconnection strategy of 20 retries over an interval of 3 seconds
messaging_service = (
    MessagingService.builder()
    .from_properties(broker_props)
    .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20, 3000))
    .build()
)

# Blocking connect thread
messaging_service.connect()
logger.info(f"Messaging Service connected? {messaging_service.is_connected}")

# Event Handling for the messaging service
service_handler = ServiceEventHandler()
messaging_service.add_reconnection_listener(service_handler)
messaging_service.add_reconnection_attempt_listener(service_handler)
messaging_service.add_service_interruption_listener(service_handler)

# Queue name.
queue_name = QUEUE_NAME
durable_non_exclusive_queue = Queue.durable_non_exclusive_queue(queue_name)

try:
    # Build a receiver and bind it to the durable exclusive queue
    persistent_receiver: PersistentMessageReceiver = (
        messaging_service.create_persistent_message_receiver_builder()
        .with_missing_resources_creation_strategy(
            MissingResourcesCreationStrategy.CREATE_ON_START
        )
        .build(durable_non_exclusive_queue)
    )
    persistent_receiver.start()

    # Callback for received messages
    persistent_receiver.receive_async(MessageHandlerImpl(persistent_receiver))
    logger.info(
        f"PERSISTENT receiver started... Bound to Queue [{durable_non_exclusive_queue.get_name()}]"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down gracefully...")
        if persistent_receiver and persistent_receiver.is_running():
            logger.info("Terminating receiver")
            persistent_receiver.terminate(grace_period=0)
        logger.info("Disconnecting Messaging Service")
        messaging_service.disconnect()

except PubSubPlusClientError as exception:
    logger.error(
        f"Make sure queue {queue_name} exists on broker! Exception: {exception}"
    )

finally:
    if persistent_receiver and persistent_receiver.is_running():
        logger.info("Terminating receiver")
        persistent_receiver.terminate(grace_period=0)
    logger.info("Disconnecting Messaging Service")
    messaging_service.disconnect()
