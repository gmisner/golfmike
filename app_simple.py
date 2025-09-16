# app_simple.py - Simplified version without monitoring dependencies
from quart import Quart, jsonify, request
from celery_app import app as celery_app
from tasks import process_xml
import time

app = Quart(__name__)

# Configure Quart app
app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True

# Optional: Link Celery app to Quart app
app.celery_app = celery_app


@app.route("/", methods=["GET"])
async def root():
    return jsonify({"message": "GolfMike API is running", "status": "healthy"})


@app.route("/process", methods=["POST"])
async def process():
    try:
        data = await request.get_json()
        xml_payload = data.get("xml_payload")
        if not xml_payload:
            return jsonify({"error": "No XML payload provided"}), 400

        # Trigger Celery task
        task = process_xml.delay(xml_payload)
        return jsonify({"task_id": task.id}), 202
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/result/<task_id>", methods=["GET"])
async def result(task_id):
    try:
        result = celery_app.AsyncResult(task_id)
        if result.state == "PENDING":
            return jsonify({"state": result.state}), 202
        elif result.state == "SUCCESS":
            return jsonify({"state": result.state, "result": result.result}), 200
        else:
            return jsonify({"state": result.state, "result": str(result.info)}), 200
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/health", methods=["GET"])
async def health():
    """Simple health check endpoint."""
    try:
        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "message": "GolfMike API is running",
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500)



