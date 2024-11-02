from celery_app import app as celery_app

# Trigger the start_solace_consumer task
task = celery_app.send_task("tasks.start_solace_consumer")
print(f"Task ID: {task.id}")
