import time

from solace.messaging.messaging_service import MessagingService, ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener, ServiceEvent
from solace.messaging.resources.queue import Queue
from solace.messaging.config.retry_strategy import RetryStrategy
from solace.messaging.receiver.direct_message_receiver import DirectMessageReceiver
from solace.messaging.receiver.message_receiver import MessageHandler, InboundMessage
from solace.messaging.errors.pubsubplus_client_error import PubSubPlusClientError
from solace.messaging.resources.share_name import ShareName
from solace.messaging.config.missing_resources_creation_configuration import MissingResourcesCreationStrategy


# Solace message broker connection parameters
# Use the TCPS scheme and the secure port
HOST = "tcps://ems2.swim.faa.gov:55443"
USERNAME = "gear.twinhawk.co"
PASSWORD = "Bke2fbKgTcKycCYdvBrPDw"
VPN_NAME = "ITWS"
SHARE_NAME = "GMITWS"
# The queue where you want to receive messages
QUEUE_NAME = "gear.twinhawk.co.ITWS.aa14567c-ba74-413d-b25c-6855a8484b9c.OUT"

# Handle received messages
class MessageHandlerImpl(MessageHandler):
    def on_message(self, message: InboundMessage):
        # Check if the payload is a String or Byte, decode if its the later
        payload = message.get_payload_as_string() if message.get_payload_as_string() != None else message.get_payload_as_bytes()
        if isinstance(payload, bytearray):
            print(f"Received a message of type: {type(payload)}. Decoding to string")
            payload = payload.decode()

        topic = message.get_destination_name()
        print("\n" + f"Message Payload String: {payload} \n")
        print("\n" + f"Message Topic: {topic} \n")
        print("\n" + f"Message dump: {message} \n")


# Inner classes for error handling
class ServiceEventHandler(ReconnectionListener, ReconnectionAttemptListener, ServiceInterruptionListener):
    '''Class representing recieved error message handler'''

    def on_reconnected(self, e: ServiceEvent):
        print("\non_reconnected")
        print(f"Error cause: {e.get_cause()}")
        print(f"Message: {e.get_message()}")

    def on_reconnecting(self, e: "ServiceEvent"):
        print("\non_reconnecting")
        print(f"Error cause: {e.get_cause()}")
        print(f"Message: {e.get_message()}")

    def on_service_interrupted(self, e: "ServiceEvent"):
        print("\non_service_interrupted")
        print(f"Error cause: {e.get_cause()}")
        print(f"Message: {e.get_message()}")


broker_props = {
    'solace.messaging.transport.host': HOST,
    'solace.messaging.service.vpn-name': VPN_NAME,
    'solace.messaging.authentication.scheme.basic.username': USERNAME,
    'solace.messaging.authentication.scheme.basic.password': PASSWORD,
    'solace.messaging.transport.security.trust-store': '/GolfMike/FAA.jks',
    'solace.messaging.transport.security.trust-store-password': 'faa.4TW!',
    "solace.messaging.tls.cert-validated": False,
    "solace.messaging.tls.cert-validated-date": False
}

# transport_security = TLS.create() \
# .with_certificate_validation(True, validate_server_name=False,
#     trust_store_file_path=".")

# service = MessagingService.builder().from_properties(broker_props)\
# .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20,3))\
# .with_transport_security_strategy(transport_security).build()

messaging_service = MessagingService.builder().from_properties(broker_props)\
    .with_reconnection_retry_strategy(RetryStrategy.parametrized_retry(20, 3000))\
    .build()

# Blocking connect thread
messaging_service.connect()
print(f'Messaging Service connected? {messaging_service.is_connected}')

# Event Handling for the messaging service
service_handler = ServiceEventHandler()
messaging_service.add_reconnection_listener(service_handler)
messaging_service.add_reconnection_attempt_listener(service_handler)
messaging_service.add_service_interruption_listener(service_handler)

# Queue name.
# NOTE: This assumes that a persistent queue already exists on the broker with the right topic subscription
non_durable_exclusive_queue = Queue.non_durable_exclusive_queue(QUEUE_NAME)

# Create a ShareName for the queue
share_name = ShareName.get_name(SHARE_NAME)


try:
  # Build a receiver and bind it to the durable exclusive queue
    direct_receiver: DirectMessageReceiver = messaging_service.create_direct_message_receiver_builder()\
        .build(share_name)
    direct_receiver.start()

 # Callback for received messages
    direct_receiver.receive_async(MessageHandlerImpl())
    print(
        f'PERSISTENT receiver started... Bound to Queue [{non_durable_exclusive_queue.get_name()}]')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nKeyboardInterrupt received')
# Handle API exception
except PubSubPlusClientError as exception:
    #print(f'\nMake sure queue {QUEUE_NAME} exists on broker!')
    print(exception)

finally:
    if direct_receiver and direct_receiver.is_running():
        print('\nTerminating receiver')
        direct_receiver.terminate(grace_period=0)
    print('\nDisconnecting Messaging Service')
    messaging_service.disconnect()
