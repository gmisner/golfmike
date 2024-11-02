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
        "tasks.start_solace_consumer": {
            "queue": "solace"
        },  # Route start_solace_consumer to 'solace' queue
    },
    task_acks_late=True,  # Acknowledge the task only after it's executed
    worker_prefetch_multiplier=1,  # Prevents overloading a worker
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
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
