# app_flask.py - Flask version to avoid Quart compatibility issues
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from celery_app import app as celery_app
from tasks import process_xml
from simple_api import create_simple_api
import time
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Optional: Link Celery app to Flask app
app.celery_app = celery_app

# Configure Flask for better response handling
app.config["JSON_SORT_KEYS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False


@app.route("/", methods=["GET"])
def root():
    """Serve the main flight tracking dashboard"""
    try:
        return send_from_directory("static", "index.html")
    except Exception as e:
        return jsonify({"error": "Frontend not available", "details": str(e)}), 500


@app.route("/index.html", methods=["GET"])
def index():
    """Serve the main flight tracking dashboard"""
    try:
        return send_from_directory("static", "index.html")
    except Exception as e:
        return jsonify({"error": "Frontend not available", "details": str(e)}), 500


@app.route("/flight-plan.html", methods=["GET"])
def flight_plan():
    """Serve the flight plan lookup page"""
    try:
        return send_from_directory("static", "flight-plan.html")
    except Exception as e:
        return (
            jsonify({"error": "Flight plan page not available", "details": str(e)}),
            500,
        )


@app.route("/flight-detail.html", methods=["GET"])
def flight_detail():
    """Serve the flight detail page"""
    try:
        return send_from_directory("static", "flight-detail.html")
    except Exception as e:
        return (
            jsonify({"error": "Flight detail page not available", "details": str(e)}),
            500,
        )


@app.route("/test-tabler.html", methods=["GET"])
def test_tabler():
    """Serve the Tabler.io test page"""
    try:
        return send_from_directory("static", "test-tabler.html")
    except Exception as e:
        return (
            jsonify({"error": "Test page not available", "details": str(e)}),
            500,
        )


@app.route("/api", methods=["GET"])
def api_root():
    return jsonify({"message": "GolfMike API is running", "status": "healthy"})


@app.route("/api/test", methods=["GET"])
def test_db():
    """Test database connection"""
    try:
        from simple_api import SessionLocal

        session = SessionLocal()
        from sqlalchemy import text

        result = session.execute(text("SELECT COUNT(*) FROM flight_plan"))
        count = result.scalar()
        session.close()
        return jsonify({"message": "Database connected", "flight_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process", methods=["POST"])
def process():
    try:
        data = request.get_json()
        xml_payload = data.get("xml_payload")
        if not xml_payload:
            return jsonify({"error": "No XML payload provided"}), 400

        # Trigger Celery task
        task = process_xml.delay(xml_payload)
        return jsonify({"task_id": task.id}), 202
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/result/<task_id>", methods=["GET"])
def result(task_id):
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
def health():
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


# Add simple flight tracking API endpoints
create_simple_api(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5500, debug=True)
