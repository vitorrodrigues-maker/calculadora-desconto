import json
import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify

from paths import bundle_path, data_file, env_file

load_dotenv(env_file())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(bundle_path(), "templates"),
    static_folder=os.path.join(bundle_path(), "static"),
)

DATA_PATH = data_file()
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_MINUTES", "10"))

_last_refresh_status = {"time": None, "ok": None, "error": None}


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def scheduled_refresh():
    """Called by APScheduler every N minutes."""
    from refresh_data import refresh_from_metabase
    try:
        result = refresh_from_metabase()
        if result:
            _last_refresh_status["time"] = datetime.now().isoformat()
            _last_refresh_status["ok"] = True
            _last_refresh_status["error"] = None
            log.info("Auto-refresh OK — %d dias", len(result["daily_discounts"]))
        else:
            _last_refresh_status["time"] = datetime.now().isoformat()
            _last_refresh_status["ok"] = False
            _last_refresh_status["error"] = "Sem dados retornados"
    except Exception as e:
        _last_refresh_status["time"] = datetime.now().isoformat()
        _last_refresh_status["ok"] = False
        _last_refresh_status["error"] = str(e)
        log.exception("Auto-refresh falhou")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    data = load_data()
    return jsonify(data)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force an immediate refresh from Metabase."""
    from refresh_data import refresh_from_metabase
    try:
        result = refresh_from_metabase()
        if result:
            _last_refresh_status["time"] = datetime.now().isoformat()
            _last_refresh_status["ok"] = True
            _last_refresh_status["error"] = None
            return jsonify({"ok": True, "days": len(result["daily_discounts"])})
        return jsonify({"ok": False, "error": "Sem dados retornados"}), 502
    except Exception as e:
        _last_refresh_status["time"] = datetime.now().isoformat()
        _last_refresh_status["ok"] = False
        _last_refresh_status["error"] = str(e)
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/status")
def api_status():
    return jsonify({
        "last_refresh": _last_refresh_status,
        "refresh_interval_minutes": REFRESH_INTERVAL,
        "scheduler_running": scheduler.running if scheduler else False,
    })


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(scheduled_refresh, "interval", minutes=REFRESH_INTERVAL, id="metabase_refresh")


def start_app(port=5050):
    """Start the app with initial refresh + scheduler. Used by launcher.py and __main__."""
    log.info("Refresh inicial ao iniciar o app...")
    scheduled_refresh()

    scheduler.start()
    log.info("Scheduler iniciado — refresh a cada %d minutos", REFRESH_INTERVAL)

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_app()
