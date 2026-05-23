# app_flask.py - Flask version to avoid Quart compatibility issues
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_jwt_extended import JWTManager
from celery_app import app as celery_app
from tasks import process_xml
from simple_api import create_simple_api
from sqlalchemy import text
import time
import os
import secrets

from utils.logger import main_logger as logger
from utils.readiness import database_connection_ok

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Optional: Link Celery app to Flask app
app.celery_app = celery_app

# Configure Flask for better response handling
app.config["JSON_SORT_KEYS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

# JWT configuration
app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY", secrets.token_hex(32)
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = 900       # 15 minutes
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 2_592_000  # 30 days

jwt = JWTManager(app)

# Token denylist check
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    from db_config import SessionLocal
    jti = jwt_payload["jti"]
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT id FROM jwt_denylist WHERE jti = :jti"),
                {"jti": jti},
            ).fetchone()
            return row is not None
    except Exception:
        return False


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


@app.route("/flight-alerts.html", methods=["GET"])
def flight_alerts_page():
    """Serve SWIM / operational alerts list for a tail number (?aircraft_id=)."""
    try:
        return send_from_directory("static", "flight-alerts.html")
    except Exception as e:
        return (
            jsonify({"error": "Flight alerts page not available", "details": str(e)}),
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


@app.route("/flights-table.html", methods=["GET"])
def flights_table():
    """Serve the flights table page"""
    try:
        return send_from_directory("static", "flights-table.html")
    except Exception as e:
        return (
            jsonify({"error": "Flights table page not available", "details": str(e)}),
            500,
        )


@app.route("/search.html", methods=["GET"])
def search_results_page():
    """Serve the search results page (same pattern as index.html, not under /static/ URL)."""
    try:
        return send_from_directory("static", "search.html")
    except Exception as e:
        return (
            jsonify({"error": "Search page not available", "details": str(e)}),
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


@app.route("/health/ready", methods=["GET"])
def health_ready():
    """Readiness: API process is up and the primary database accepts connections."""
    ok, err = database_connection_ok()
    ts = time.time()
    if ok:
        return (
            jsonify(
                {
                    "status": "ready",
                    "timestamp": ts,
                    "database": {"ok": True},
                }
            ),
            200,
        )
    if err:
        logger.warning("readiness check failed: {}", err)
    return (
        jsonify(
            {
                "status": "not_ready",
                "timestamp": ts,
                "database": {"ok": False, "error": err or "unknown"},
            }
        ),
        503,
    )


# Add simple flight tracking API endpoints
create_simple_api(app)

# Register v1 API blueprints
from api.v1 import flights as v1_flights
from api.v1 import airports as v1_airports
from api.v1 import events as v1_events
from api.v1 import status as v1_status
from api.v1 import auth as v1_auth

app.register_blueprint(v1_flights.bp)
app.register_blueprint(v1_airports.bp)
app.register_blueprint(v1_events.bp)
app.register_blueprint(v1_status.bp)
app.register_blueprint(v1_auth.bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5500"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    # Werkzeug stat reloader restarts the process on file changes; with Docker bind mounts that
    # is noisy and often drops in-flight TCP connections (curl "empty reply"). Opt-in only.
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    logger.info(
        "Starting Flask on 0.0.0.0:{} debug={} use_reloader={} threaded=True",
        port,
        debug,
        use_reloader,
    )
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=use_reloader,
        threaded=True,
    )
