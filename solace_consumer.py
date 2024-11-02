import time
import concurrent.futures
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
from utils.logger import main_logger as logger
from celery_app import app as celery_app

# Solace message broker connection parameters
HOST = "tcps://ems1.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "TFMS"
QUEUE_NAME = "gear.twinhawk.co.TFMS.b70b3338-3b0e-4388-bba0-b49d870a502c.OUT"

# Thread pool for concurrent message processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


class MessageHandlerImpl(MessageHandler):
    def __init__(self, persistent_receiver: PersistentMessageReceiver):
        # Store the receiver instance for later use
        self.receiver: PersistentMessageReceiver = persistent_receiver

    def on_message(self, message: InboundMessage):
        # Submit the message to the thread pool for asynchronous processing
        executor.submit(self.process_message, message)

    def process_message(self, message: InboundMessage):
        # Delay import to avoid circular dependency
        from tasks import process_xml

        # Extract the message payload, first trying as a string
        payload = message.get_payload_as_string()
        if payload is None:
            # If the payload is not a string, try getting it as bytes and decode if necessary
            payload = message.get_payload_as_bytes()
            if isinstance(payload, (bytearray, bytes)):
                logger.info(
                    f"Received a message of type: {type(payload)}. Decoding to string."
                )
                payload = payload.decode()

        try:
            # Trigger a Celery task for processing the XML payload
            logger.info("Triggering Celery task to process the XML payload.")
            logger.debug(f"Payload received for Celery task: {payload}")
            task = celery_app.send_task("tasks.process_xml", args=[payload])
            logger.info(f"Celery task {task.id} started for processing message.")

        except Exception as e:
            # Log any exception that occurs during message processing
            logger.error(f"Error processing message: {e}", exc_info=True)


class ServiceEventHandler(
    ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener
):
    def on_reconnected(self, e: ServiceEvent):
        # Log details when the service successfully reconnects
        logger.info("Reconnected to the service")
        logger.info(f"Error cause: {e.get_cause()}")
        logger.info(f"Message: {e.get_message()}")

    def on_reconnecting(self, e: "ServiceEvent"):
        # Log details when attempting to reconnect to the service
        logger.info("Attempting to reconnect to the service")
        logger.info(f"Error cause: {e.get_cause()}")
        logger.info(f"Message: {e.get_message()}")

    def on_service_interrupted(self, e: "ServiceEvent"):
        # Log details when the service is interrupted
        logger.warning("Service interrupted")
        logger.warning(f"Error cause: {e.get_cause()}")
        logger.warning(f"Message: {e.get_message()}")


def run():
    # Broker configuration for connecting to the Solace message broker
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

    # Build a messaging service with a reconnection strategy of 20 retries over an interval of 3 seconds
    messaging_service = (
        MessagingService.builder()
        .from_properties(broker_props)
        .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20, 3000))
        .build()
    )

    # Connect to the messaging service (blocking call)
    messaging_service.connect()
    logger.info(f"Messaging Service connected? {messaging_service.is_connected}")

    # Event Handling for the messaging service (reconnection, interruption, etc.)
    service_handler = ServiceEventHandler()
    messaging_service.add_reconnection_listener(service_handler)
    messaging_service.add_reconnection_attempt_listener(service_handler)
    messaging_service.add_service_interruption_listener(service_handler)

    # Create a durable, non-exclusive queue to bind the message receiver
    queue_name = QUEUE_NAME
    durable_non_exclusive_queue = Queue.durable_non_exclusive_queue(queue_name)

    persistent_receiver = None  # Initialize persistent_receiver before the try block

    try:
        # Build a persistent message receiver and bind it to the queue
        persistent_receiver: PersistentMessageReceiver = (
            messaging_service.create_persistent_message_receiver_builder()
            .with_missing_resources_creation_strategy(
                MissingResourcesCreationStrategy.CREATE_ON_START
            )
            .build(durable_non_exclusive_queue)
        )
        persistent_receiver.start()

        # Set up the callback for received messages using the custom message handler
        persistent_receiver.receive_async(MessageHandlerImpl(persistent_receiver))
        logger.info(
            f"PERSISTENT receiver started... Bound to Queue [{durable_non_exclusive_queue.get_name()}]"
        )

        try:
            # Run indefinitely to keep the consumer active
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Handle graceful shutdown on keyboard interrupt
            logger.info("KeyboardInterrupt received. Shutting down gracefully...")
        finally:
            # Terminate the receiver and disconnect the messaging service
            if persistent_receiver and persistent_receiver.is_running():
                logger.info("Terminating receiver")
                persistent_receiver.terminate(grace_period=0)
            logger.info("Disconnecting Messaging Service")
            messaging_service.disconnect()

    except PubSubPlusClientError as exception:
        # Handle errors related to the Solace messaging client
        logger.error(
            f"Make sure queue {queue_name} exists on broker! Exception: {exception}"
        )

    finally:
        # Ensure the receiver is terminated and the messaging service is disconnected
        if persistent_receiver and persistent_receiver.is_running():
            logger.info("Terminating receiver")
            persistent_receiver.terminate(grace_period=0)
        logger.info("Disconnecting Messaging Service")
        messaging_service.disconnect()
