import time
import sys
import os
from lxml import objectify, etree
from collections import OrderedDict
import re
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

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.weather_parser import WeatherXMLParser
from storers.weather_storer import WeatherDataStorer
from utils.logger import main_logger as logger


# Solace message broker connection parameters
# Use the TCPS scheme and the secure port
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "ITWS"
# The queue where you want to receive messages
QUEUE_NAME = "gear.twinhawk.co.ITWS.35078235-3acd-40a5-931f-f9e15c04f7da.OUT"


# Initialize weather processing components
weather_parser = WeatherXMLParser()
weather_storer = WeatherDataStorer()


# Handle received messages
class MessageHandlerImpl(MessageHandler):
    def on_message(self, message: InboundMessage):
        try:
            # Check if the payload is a String or Byte, decode if its the later
            payload = (
                message.get_payload_as_string()
                if message.get_payload_as_string() != None
                else message.get_payload_as_bytes()
            )
            if isinstance(payload, bytearray):
                logger.info(
                    f"Received a message of type: {type(payload)}. Decoding to string"
                )
                payload = payload.decode()

            topic = message.get_destination_name()
            logger.info(f"🌤️  Received weather message from topic: {topic}")

            # Parse the weather XML data
            if payload and payload.strip():
                try:
                    weather_data = weather_parser.parse_message(payload)

                    if "error" in weather_data:
                        logger.error(
                            f"❌ Error parsing weather data: {weather_data['error']}"
                        )
                    else:
                        logger.info(
                            f"✅ Parsed {weather_data.get('type', 'UNKNOWN')} weather data"
                        )

                        # Store the weather data
                        if weather_storer.store_weather_data(weather_data):
                            logger.info(
                                f"💾 Successfully stored {weather_data.get('type', 'UNKNOWN')} data"
                            )
                        else:
                            logger.error(
                                f"❌ Failed to store {weather_data.get('type', 'UNKNOWN')} data"
                            )

                except Exception as e:
                    logger.error(f"❌ Error processing weather message: {e}")
                    logger.debug(
                        f"Raw payload: {payload[:500]}..."
                    )  # Log first 500 chars
            else:
                logger.warning("⚠️  Received empty weather message payload")

        except Exception as e:
            logger.error(f"❌ Error in weather message handler: {e}")


# Inner classes for error handling
class ServiceEventHandler(
    ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener
):
    def on_reconnected(self, e: ServiceEvent):
        logger.info("🔄 Weather service reconnected")
        logger.info(f"Error cause: {e.get_cause()}")
        logger.info(f"Message: {e.get_message()}")

    def on_reconnecting(self, e: "ServiceEvent"):
        logger.warning("🔄 Weather service reconnecting...")
        logger.warning(f"Error cause: {e.get_cause()}")
        logger.warning(f"Message: {e.get_message()}")

    def on_service_interrupted(self, e: "ServiceEvent"):
        logger.error("❌ Weather service interrupted")
        logger.error(f"Error cause: {e.get_cause()}")
        logger.error(f"Message: {e.get_message()}")


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

# transport_security = TLS.create() \
# .with_certificate_validation(True, validate_server_name=False,
#     trust_store_file_path=".")

# service = MessagingService.builder().from_properties(broker_props)\
# .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20,3))\
# .with_transport_security_strategy(transport_security).build()

messaging_service = (
    MessagingService.builder()
    .from_properties(broker_props)
    .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20, 3000))
    .build()
)


def run_weather_subscription():
    """Main function to run the weather subscription service"""
    try:
        logger.info("🌤️  Starting Weather Subscription Service...")

        # Blocking connect thread
        messaging_service.connect()
        logger.info(
            f"✅ Weather Messaging Service connected: {messaging_service.is_connected}"
        )

        # Event Handling for the messaging service
        service_handler = ServiceEventHandler()
        messaging_service.add_reconnection_listener(service_handler)
        messaging_service.add_reconnection_attempt_listener(service_handler)
        messaging_service.add_service_interruption_listener(service_handler)

        # Queue name.
        # NOTE: This assumes that a persistent queue already exists on the broker with the right topic subscription
        queue_name = QUEUE_NAME
        durable_non_exclusive_queue = Queue.durable_non_exclusive_queue(queue_name)

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
        persistent_receiver.receive_async(MessageHandlerImpl())
        logger.info(
            f"🎯 Weather receiver started... Bound to Queue [{durable_non_exclusive_queue.get_name()}]"
        )

        # Get initial weather data summary
        weather_summary = weather_storer.get_weather_summary()
        logger.info(f"📊 Current weather data: {weather_summary}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 KeyboardInterrupt received - shutting down weather service")

    except PubSubPlusClientError as exception:
        logger.error(f"❌ Weather service error: {exception}")
        logger.error(f"Make sure queue {queue_name} exists on broker!")
    except Exception as e:
        logger.error(f"❌ Unexpected error in weather service: {e}")
    finally:
        if (
            "persistent_receiver" in locals()
            and persistent_receiver
            and persistent_receiver.is_running()
        ):
            logger.info("🛑 Terminating weather receiver")
            persistent_receiver.terminate(grace_period=0)
        logger.info("🛑 Disconnecting Weather Messaging Service")
        messaging_service.disconnect()


if __name__ == "__main__":
    run_weather_subscription()
