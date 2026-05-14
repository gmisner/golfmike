from celery import Celery
from kombu import Queue
import os

_broker = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

app = Celery("GolfMike", broker=_broker, backend=_backend)

app.conf.update(
    task_routes={
        "tasks.process_xml": {"queue": "message_processing"},
        "tasks.start_solace_consumer": {"queue": "solace"},
        "tasks.process_flight_plan_xml": {"queue": "message_processing"},
        "tasks.start_flight_plan_consumer": {"queue": "solace"},
        "tasks.fetch_aviation_weather": {"queue": "weather_processing"},
        "tasks.fetch_flight_weather": {"queue": "weather_processing"},
        "tasks.refresh_flow_predictions": {"queue": "weather_processing"},
        "tasks.cleanup_old_weather_data": {"queue": "maintenance"},
        "tasks.label_completed_flow_predictions": {"queue": "maintenance"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=2,
    task_soft_time_limit=300,
    task_time_limit=600,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_accept_content=["json"],
    result_expires=3600,
    result_persistent=True,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    timezone="UTC",
    enable_utc=True,
    task_compression="gzip",
    result_compression="gzip",
)

app.conf.task_queues = (
    Queue("solace", exchange="solace", routing_key="solace.#"),
    Queue("message_processing", exchange="message_processing", routing_key="message_processing.#"),
    Queue("weather_processing", exchange="weather_processing", routing_key="weather_processing.#"),
    Queue("maintenance", exchange="maintenance", routing_key="maintenance.#"),
)

# Wire the beat schedule from celery_beat_schedule.py
from celery_beat_schedule import beat_schedule, timezone as beat_timezone  # noqa: E402
app.conf.beat_schedule = beat_schedule
app.conf.timezone = beat_timezone
app.conf.beat_schedule_filename = os.getenv("CELERY_BEAT_SCHEDULE_FILE", "/tmp/celerybeat-schedule")

app.autodiscover_tasks(["tasks"])
