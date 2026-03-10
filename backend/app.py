"""
Flask REST API Server
Serves the frontend dashboard and exposes AI bottleneck-detection endpoints.
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from backend.monitor import SystemMonitor
from backend.detector import BottleneckDetector
from backend.recommender import Recommender

# ── App setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app)

monitor = SystemMonitor()
detector = BottleneckDetector()
recommender = Recommender()


# ── Static file serving ──────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the frontend dashboard."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve static assets (CSS, JS, images)."""
    return send_from_directory(BASE_DIR, filename)


# ── API endpoints ────────────────────────────────────────────────────────────

@app.route("/api/metrics")
def api_metrics():
    """
    GET /api/metrics
    Returns current CPU %, GPU %, memory %, and PCIe throughput.
    """
    try:
        metrics = monitor.get_all_metrics()
        return jsonify({"status": "ok", "data": metrics})
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/detect")
def api_detect():
    """
    GET /api/detect
    Runs the bottleneck detector and returns detected bottlenecks with
    type, severity, confidence score, description, and timestamp.
    """
    try:
        bottlenecks = detector.detect()
        return jsonify({"status": "ok", "data": bottlenecks})
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/recommend")
def api_recommend():
    """
    GET /api/recommend
    Detects current bottlenecks and returns tailored optimisation strategies.
    """
    try:
        bottlenecks = detector.detect()
        recommendations = recommender.recommend(bottlenecks)
        return jsonify({"status": "ok", "data": recommendations})
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"status": "error", "message": str(exc)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
