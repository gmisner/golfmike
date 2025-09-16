# app.py
from quart import Quart, jsonify, request
from celery_app import app as celery_app  # Import the Celery app
from tasks import process_xml
from utils.logger import main_logger as logger
from monitoring import get_health_status, SystemMonitor

app = Quart(__name__)

# Configure Quart app
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True

# Optional: Link Celery app to Quart app
app.celery_app = celery_app


@app.route("/process", methods=["POST"])
async def process():
    try:
        data = await request.get_json()
        xml_payload = data.get("xml_payload")
        if not xml_payload:
            return jsonify({"error": "No XML payload provided"}), 400

        # Trigger Celery task
        task = process_xml.delay(xml_payload)
        logger.info(f"Started Celery task: {task.id}")
        return jsonify({"task_id": task.id}), 202
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/result/<task_id>", methods=["GET"])
async def result(task_id):
    try:
        result = celery_app.AsyncResult(task_id)  # Use Celery app to get task result
        if result.state == "PENDING":
            return jsonify({"state": result.state}), 202
        elif result.state == "SUCCESS":
            return jsonify({"state": result.state, "result": result.result}), 200
        else:
            return jsonify({"state": result.state, "result": str(result.info)}), 200
    except Exception as e:
        logger.error(f"Error retrieving task result: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/health", methods=["GET"])
async def health():
    """Health check endpoint."""
    try:
        health_data = get_health_status()
        status_code = 200 if health_data["status"] == "healthy" else 503
        return jsonify(health_data), status_code
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/metrics", methods=["GET"])
async def metrics():
    """System metrics endpoint."""
    try:
        metrics = SystemMonitor.get_system_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/stats", methods=["GET"])
async def stats():
    """Processing statistics endpoint."""
    try:
        stats = SystemMonitor.get_processing_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)
