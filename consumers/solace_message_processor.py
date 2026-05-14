"""
Enhanced Solace Message Processor - Based on FAA JMS Client patterns
Provides high-performance message processing with queue management
"""

import time
import threading
import queue
from typing import Callable, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, Future
from solace.messaging.receiver.persistent_message_receiver import (
    PersistentMessageReceiver,
)
from solace.messaging.receiver.message_receiver import MessageHandler, InboundMessage
from solace.messaging.resources.queue import Queue
from utils.logger import main_logger as logger


class SolaceMessageProcessor:
    """
    High-performance message processor based on FAA JMS Client patterns
    Manages concurrent consumers and parallel processing with queue management
    """

    def __init__(
        self,
        concurrent_consumer_count: int = 4,
        parallel_processor_count: int = 2,
        processing_queue_size: int = 10000,
        message_handler: Optional[Callable] = None,
    ):
        self.concurrent_consumer_count = concurrent_consumer_count
        self.parallel_processor_count = parallel_processor_count
        self.processing_queue_size = processing_queue_size
        self.message_handler = message_handler

        # Processing queue and thread pool
        self.processing_queue = queue.Queue(maxsize=processing_queue_size)
        self.processor_executor = ThreadPoolExecutor(
            max_workers=parallel_processor_count, thread_name_prefix="SolaceProcessor"
        )

        # Consumer management
        self.consumers = []
        self.consumer_executor = ThreadPoolExecutor(
            max_workers=concurrent_consumer_count, thread_name_prefix="SolaceConsumer"
        )

        # State management
        self.is_running = False
        self.is_consuming = True
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "queue_size": 0,
            "start_time": None,
        }

        # Threading
        self.consumer_threads = []
        self.processor_threads = []

        logger.info(
            f"Initialized SolaceMessageProcessor: {concurrent_consumer_count} consumers, "
            f"{parallel_processor_count} processors, queue size {processing_queue_size}"
        )

    def start(self, messaging_service, queue_name: str):
        """
        Start the message processor with multiple consumers
        Based on FAA JMS Client JmsMessageProcessor.start() pattern
        """
        if self.is_running:
            logger.warning("Message processor is already running")
            return

        logger.info(f"Starting message processor for queue: {queue_name}")

        self.is_running = True
        self.is_consuming = True
        self.stats["start_time"] = time.time()

        # Create multiple consumers for concurrent message consumption
        for i in range(self.concurrent_consumer_count):
            try:
                # Create queue object
                queue_obj = Queue.durable_exclusive_queue(queue_name)

                # Create persistent message receiver
                persistent_receiver = (
                    messaging_service.create_persistent_message_receiver_builder()
                    .with_message_auto_acknowledgement()
                    .build(queue_obj)
                )

                # Create message handler
                handler = SolaceMessageHandler(
                    persistent_receiver=persistent_receiver, processor=self
                )

                # Start consumer
                persistent_receiver.start()
                persistent_receiver.receive_async(handler)

                self.consumers.append(persistent_receiver)

                logger.info(
                    f"Started consumer {i + 1}/{self.concurrent_consumer_count}"
                )

            except Exception as e:
                logger.error(f"Failed to start consumer {i + 1}: {e}")

        # Start processor threads
        for i in range(self.parallel_processor_count):
            thread = threading.Thread(
                target=self._processor_loop, name=f"Processor-{i + 1}", daemon=True
            )
            thread.start()
            self.processor_threads.append(thread)

        logger.info(
            f"Message processor started with {len(self.consumers)} consumers and "
            f"{self.parallel_processor_count} processors"
        )

    def stop(self):
        """
        Stop the message processor gracefully
        Based on FAA JMS Client JmsMessageProcessor.stop() pattern
        """
        if not self.is_running:
            return

        logger.info("Stopping message processor...")

        # Stop consuming new messages
        self.is_consuming = False

        # Stop consumers
        for consumer in self.consumers:
            try:
                consumer.stop()
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")

        self.consumers.clear()

        # Stop processing
        self.is_running = False

        # Shutdown executors
        self.consumer_executor.shutdown(wait=True)
        self.processor_executor.shutdown(wait=True)

        # Wait for processor threads
        for thread in self.processor_threads:
            thread.join(timeout=5)

        self.processor_threads.clear()

        logger.info("Message processor stopped")

    def _processor_loop(self):
        """Main processing loop for handling queued messages"""
        while self.is_running:
            try:
                # Check if we should resume consumption (queue has space)
                self.resume_consumption()
                
                # Get message from queue with timeout
                try:
                    message_data = self.processing_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Process message
                self._process_message(message_data)

                # Mark task as done
                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Error in processor loop: {e}", exc_info=True)
                self.stats["messages_failed"] += 1

    def _process_message(self, message_data: Dict[str, Any]):
        """Process a single message"""
        try:
            if self.message_handler:
                self.message_handler(message_data)
            else:
                logger.warning("No message handler configured")

            self.stats["messages_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.stats["messages_failed"] += 1

    def queue_message(self, message: InboundMessage):
        """
        Queue a message for processing
        If queue is full, consumption will be paused until space is available
        """
        if not self.is_consuming:
            logger.warning("Message consumption is paused - queue full")
            return False

        try:
            # Extract message data
            message_data = {
                "payload": message.get_payload_as_string(),
                "timestamp": time.time(),
                "message_id": getattr(message, "message_id", None),
                "destination": getattr(message, "destination", None),
            }

            # Add to processing queue
            self.processing_queue.put_nowait(message_data)
            self.stats["messages_received"] += 1
            self.stats["queue_size"] = self.processing_queue.qsize()

            return True

        except queue.Full:
            # Queue is full - pause consumption
            logger.warning(
                f"Processing queue is full ({self.processing_queue_size} messages)"
            )
            self.is_consuming = False
            return False
        except Exception as e:
            logger.error(f"Error queuing message: {e}", exc_info=True)
            return False

    def resume_consumption(self):
        """Resume message consumption when queue has space"""
        if not self.is_consuming:
            queue_size = self.processing_queue.qsize()
            threshold = int(self.processing_queue_size * 0.8)
            if queue_size < threshold:
                self.is_consuming = True
                logger.info(f"✅ Resumed message consumption (queue: {queue_size}/{self.processing_queue_size}, threshold: {threshold})")

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        uptime = (
            time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        )

        return {
            **self.stats,
            "queue_size": self.processing_queue.qsize(),
            "processing_queue_size": self.processing_queue_size,
            "is_consuming": self.is_consuming,
            "uptime": uptime,
            "messages_per_second": (
                self.stats["messages_processed"] / uptime if uptime > 0 else 0
            ),
        }


class SolaceMessageHandler(MessageHandler):
    """Message handler that integrates with the message processor"""

    def __init__(
        self,
        persistent_receiver: PersistentMessageReceiver,
        processor: SolaceMessageProcessor,
    ):
        self.persistent_receiver = persistent_receiver
        self.processor = processor

    def on_message(self, message: InboundMessage):
        """Handle incoming message"""
        try:
            # Queue message for processing
            success = self.processor.queue_message(message)

            if not success:
                logger.warning("Failed to queue message - processor may be overwhelmed")

        except Exception as e:
            logger.error(f"Error in message handler: {e}", exc_info=True)
