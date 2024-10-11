from celery import Celery

# Create a Celery instance
app = Celery(
    "celery_config", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

# Optional configuration settings
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
