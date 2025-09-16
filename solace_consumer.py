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
from solace_connection_monitor import update_message_timestamp
from solace_keepalive import start_keepalive, stop_keepalive
from celery_app import app as celery_app

# Solace message broker connection parameters
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "TFMS"
QUEUE_NAME = "gear.twinhawk.co.TFMS.39cf9ef5-e72e-4d5c-bd12-f700b6b725c3.OUT"

# Thread pool for concurrent message processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# Global variable to track last message time for connection monitoring
last_message_time = time.time()


class MessageHandlerImpl(MessageHandler):
    def __init__(self, persistent_receiver: PersistentMessageReceiver):
        # Store the receiver instance for later use
        self.receiver: PersistentMessageReceiver = persistent_receiver

    def on_message(self, message: InboundMessage):
        # Update the last message timestamp for connection monitoring
        global last_message_time
        last_message_time = time.time()

        # Log detailed message information
        logger.info(
            f"📨 MESSAGE RECEIVED - Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        try:
            payload_bytes = message.get_payload_as_bytes()
            payload_size = len(payload_bytes) if payload_bytes else 0
            logger.info(f"📨 Payload Size: {payload_size} bytes")
        except:
            logger.info(f"📨 Payload Size: Unknown")

        try:
            destination = message.get_destination()
            logger.info(f"📨 Destination: {destination}")
        except:
            logger.info(f"📨 Destination: Unknown")

        try:
            ttl = message.get_time_to_live()
            logger.info(f"📨 Time to Live: {ttl}")
        except:
            logger.info(f"📨 Time to Live: Unknown")

        try:
            correlation_id = message.get_correlation_id()
            logger.info(f"📨 Correlation ID: {correlation_id}")
        except:
            logger.info(f"📨 Correlation ID: None")

        # Submit the message to the thread pool for asynchronous processing
        executor.submit(self.process_message, message)

    def process_message(self, message: InboundMessage):
        # Delay import to avoid circular dependency
        from tasks import process_xml

        logger.info(f"🔄 PROCESSING MESSAGE - Starting message processing")

        # Extract the message payload, first trying as a string
        payload = message.get_payload_as_string()
        if payload is None:
            # If the payload is not a string, try getting it as bytes and decode if necessary
            payload = message.get_payload_as_bytes()
            if isinstance(payload, (bytearray, bytes)):
                logger.info(
                    f"🔄 Received a message of type: {type(payload)}. Decoding to string."
                )
                payload = payload.decode()

        try:
            # Update connection monitor timestamp
            update_message_timestamp()
            logger.info(f"🔄 Connection monitor timestamp updated")

            # Trigger a Celery task for processing the XML payload
            logger.info("🔄 Triggering Celery task to process the XML payload.")
            logger.debug(
                f"🔄 Payload received for Celery task: {payload[:200]}..."
            )  # Log first 200 chars
            task = celery_app.send_task("tasks.process_xml", args=[payload])
            logger.info(f"✅ Celery task {task.id} started for processing message.")

        except Exception as e:
            # Log any exception that occurs during message processing
            logger.error(f"❌ Error processing message: {e}", exc_info=True)


class ServiceEventHandler(
    ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener
):
    def on_reconnected(self, e: ServiceEvent):
        # Log details when the service successfully reconnects
        logger.info("🟢 RECONNECTED - Service successfully reconnected")
        logger.info(f"🟢 Error cause: {e.get_cause()}")
        logger.info(f"🟢 Message: {e.get_message()}")
        logger.info(f"🟢 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    def on_reconnecting(self, e: "ServiceEvent"):
        # Log details when attempting to reconnect to the service
        logger.warning("🟡 RECONNECTING - Attempting to reconnect to the service")
        logger.warning(f"🟡 Error cause: {e.get_cause()}")
        logger.warning(f"🟡 Message: {e.get_message()}")
        logger.warning(f"🟡 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    def on_service_interrupted(self, e: "ServiceEvent"):
        # Log details when the service is interrupted
        logger.error("🔴 SERVICE INTERRUPTED - Service connection interrupted")
        logger.error(f"🔴 Error cause: {e.get_cause()}")
        logger.error(f"🔴 Message: {e.get_message()}")
        logger.error(f"🔴 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")


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
        # Connection timeout and keep-alive settings - aggressive timeouts for faster detection
        "solace.messaging.transport.connect-timeout": 10000,  # 10 seconds
        "solace.messaging.transport.read-timeout": 10000,  # 10 seconds
        "solace.messaging.transport.keep-alive": True,
        "solace.messaging.transport.keep-alive-interval": 5000,  # 5 seconds in milliseconds
        "solace.messaging.transport.keep-alive-idle": 10000,  # 10 seconds in milliseconds
        "solace.messaging.transport.keep-alive-count": 3,
    }

    # Build a messaging service with a reconnection strategy of 20 retries over an interval of 3 seconds
    messaging_service = (
        MessagingService.builder()
        .from_properties(broker_props)
        .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20, 3000))
        .build()
    )

    # Connect to the messaging service (blocking call)
    logger.info("🔌 CONNECTING - Attempting to connect to Solace messaging service...")
    logger.info(f"🔌 Host: {HOST}")
    logger.info(f"🔌 VPN: {VPN_NAME}")
    logger.info(f"🔌 Username: {USERNAME}")
    logger.info(f"🔌 Queue: {QUEUE_NAME}")

    messaging_service.connect()
    logger.info(
        f"🔌 CONNECTED - Messaging Service connected? {messaging_service.is_connected}"
    )
    logger.info(f"🔌 Connection timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

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
        logger.info("🎯 STARTING RECEIVER - Starting persistent message receiver...")
        persistent_receiver.start()
        logger.info("🎯 RECEIVER STARTED - Persistent receiver started successfully")

        # Set up the callback for received messages using the custom message handler
        persistent_receiver.receive_async(MessageHandlerImpl(persistent_receiver))
        logger.info(
            f"🎯 RECEIVER BOUND - PERSISTENT receiver started... Bound to Queue [{durable_non_exclusive_queue.get_name()}]"
        )
        logger.info(f"🎯 Receiver status: {persistent_receiver.is_running()}")
        logger.info(f"🎯 Receiver timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Start keep-alive mechanism to prevent connection timeouts
        logger.info("💓 STARTING KEEP-ALIVE - Starting keep-alive mechanism...")
        start_keepalive(messaging_service)
        logger.info("💓 KEEP-ALIVE STARTED - Keep-alive mechanism started successfully")

        try:
            # Run indefinitely to keep the consumer active with connection monitoring
            last_message_time = time.time()
            connection_check_interval = 10  # Check connection every 10 seconds
            max_silence_duration = 30  # Restart if no messages for 30 seconds

            logger.info(
                "🔄 MONITORING STARTED - Starting connection monitoring loop..."
            )
            logger.info(
                f"🔄 Connection check interval: {connection_check_interval} seconds"
            )
            logger.info(f"🔄 Max silence duration: {max_silence_duration} seconds")
            logger.info(
                f"🔄 Monitoring started at: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            while True:
                time.sleep(1)

                # Check connection health periodically
                current_time = time.time()
                time_since_last_message = current_time - last_message_time

                # Check for message silence first (most important - check every second)
                if time_since_last_message > max_silence_duration:
                    logger.error(
                        f"🔴 SILENCE DETECTED - No messages received for {time_since_last_message:.1f} seconds (limit: {max_silence_duration}s). Restarting connection..."
                    )
                    break

                # Check connection status every 10 seconds
                if time_since_last_message > connection_check_interval:
                    # Check if messaging service is still connected
                    if not messaging_service.is_connected:
                        logger.error(
                            f"🔴 SERVICE DISCONNECTED - Messaging service disconnected! Time since last message: {time_since_last_message:.1f}s"
                        )
                        break

                    # Check if receiver is still running
                    if not persistent_receiver.is_running():
                        logger.error(
                            f"🔴 RECEIVER STOPPED - Persistent receiver stopped! Time since last message: {time_since_last_message:.1f}s"
                        )
                        break

                    # Log periodic status (every 10 seconds)
                    logger.info(
                        f"🟢 STATUS CHECK - Service connected: {messaging_service.is_connected}, Receiver running: {persistent_receiver.is_running()}, Time since last message: {time_since_last_message:.1f}s"
                    )

        except KeyboardInterrupt:
            # Handle graceful shutdown on keyboard interrupt
            logger.info(
                "⚠️ KEYBOARD INTERRUPT - KeyboardInterrupt received. Shutting down gracefully..."
            )
        finally:
            # Stop keep-alive mechanism
            logger.info("💓 STOPPING KEEP-ALIVE - Stopping keep-alive mechanism...")
            stop_keepalive()

            # Terminate the receiver and disconnect the messaging service
            if persistent_receiver and persistent_receiver.is_running():
                logger.info(
                    "🎯 TERMINATING RECEIVER - Terminating persistent receiver..."
                )
                persistent_receiver.terminate(grace_period=0)
                logger.info("🎯 RECEIVER TERMINATED - Persistent receiver terminated")
            logger.info("🔌 DISCONNECTING - Disconnecting Messaging Service...")
            messaging_service.disconnect()
            logger.info("🔌 DISCONNECTED - Messaging Service disconnected")

    except PubSubPlusClientError as exception:
        # Handle errors related to the Solace messaging client
        logger.error(f"❌ SOLACE CLIENT ERROR - PubSubPlusClientError occurred!")
        logger.error(f"❌ Error details: {exception}")
        logger.error(f"❌ Make sure queue {queue_name} exists on broker!")
        logger.error(f"❌ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    finally:
        # Stop keep-alive mechanism
        logger.info(
            "💓 STOPPING KEEP-ALIVE (FINALLY) - Stopping keep-alive mechanism..."
        )
        stop_keepalive()

        # Ensure the receiver is terminated and the messaging service is disconnected
        if persistent_receiver and persistent_receiver.is_running():
            logger.info(
                "🎯 TERMINATING RECEIVER (FINALLY) - Terminating persistent receiver..."
            )
            persistent_receiver.terminate(grace_period=0)
            logger.info(
                "🎯 RECEIVER TERMINATED (FINALLY) - Persistent receiver terminated"
            )
        logger.info("🔌 DISCONNECTING (FINALLY) - Disconnecting Messaging Service...")
        messaging_service.disconnect()
        logger.info("🔌 DISCONNECTED (FINALLY) - Messaging Service disconnected")
