from celery import Celery
from kombu import Queue

# Initialize the Celery app
app = Celery(
    "GolfMike",
    broker="redis://redis:6379/0",  # Redis broker
    backend="redis://redis:6379/0",  # Redis result backend
)

# Set Celery configuration options
app.conf.update(
    task_routes={
        "tasks.process_xml": {"queue": "message_processing"},
        "tasks.start_solace_consumer": {"queue": "solace"},
    },
    # Task execution settings
    task_acks_late=True,  # Acknowledge the task only after it's executed
    worker_prefetch_multiplier=2,  # Allow 2 tasks per worker for better throughput
    task_soft_time_limit=300,  # 5 minute soft time limit
    task_time_limit=600,  # 10 minute hard time limit
    task_reject_on_worker_lost=True,  # Reject tasks if worker is lost
    # Serialization settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_accept_content=["json"],
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_max_memory_per_child=200000,  # Restart worker if memory exceeds 200MB
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Timezone settings
    timezone="UTC",
    enable_utc=True,
    # Task execution optimization
    task_compression="gzip",  # Compress large tasks
    result_compression="gzip",  # Compress large results
)

# Define custom task queues for different purposes
app.conf.task_queues = (
    Queue(
        "solace", exchange="solace", routing_key="solace.#"
    ),  # Queue for Solace consumers
    Queue(
        "message_processing",
        exchange="message_processing",
        routing_key="message_processing.#",
    ),  # Queue for message processing
)
# Autodiscover tasks in the specified module(s)
app.autodiscover_tasks(["tasks"])

# Optional: Add further configurations if needed
