import json
import logging
import os
from datetime import datetime, timezone, timedelta
from functools import wraps

BRT = timezone(timedelta(hours=-3))

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

from paths import bundle_path, data_file, env_file

load_dotenv(env_file())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(bundle_path(), "templates"),
    static_folder=os.path.join(bundle_path(), "static"),
)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32).hex())

DATA_PATH = data_file()
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_MINUTES", "10"))
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

_last_refresh_status = {"time": None, "ok": None, "error": None}


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Não autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def scheduled_refresh():
    """Called by APScheduler every N minutes."""
    from refresh_data import refresh_from_metabase
    try:
        result = refresh_from_metabase()
        if result:
            _last_refresh_status["time"] = datetime.now(BRT).isoformat()
            _last_refresh_status["ok"] = True
            _last_refresh_status["error"] = None
            log.info("Auto-refresh OK — %d dias", len(result["daily_discounts"]))
        else:
            _last_refresh_status["time"] = datetime.now(BRT).isoformat()
            _last_refresh_status["ok"] = False
            _last_refresh_status["error"] = "Sem dados retornados"
    except Exception as e:
        _last_refresh_status["time"] = datetime.now(BRT).isoformat()
        _last_refresh_status["ok"] = False
        _last_refresh_status["error"] = str(e)
        log.exception("Auto-refresh falhou")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Senha incorreta"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@require_auth
def index():
    return render_template("index.html")


@app.route("/api/data")
@require_auth
def api_data():
    data = load_data()
    return jsonify(data)


@app.route("/api/refresh", methods=["POST"])
@require_auth
def api_refresh():
    """Force an immediate refresh from Metabase."""
    from refresh_data import refresh_from_metabase
    try:
        result = refresh_from_metabase()
        if result:
            _last_refresh_status["time"] = datetime.now(BRT).isoformat()
            _last_refresh_status["ok"] = True
            _last_refresh_status["error"] = None
            return jsonify({"ok": True, "days": len(result["daily_discounts"])})
        return jsonify({"ok": False, "error": "Sem dados retornados"}), 502
    except Exception as e:
        _last_refresh_status["time"] = datetime.now(BRT).isoformat()
        _last_refresh_status["ok"] = False
        _last_refresh_status["error"] = str(e)
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/status")
@require_auth
def api_status():
    return jsonify({
        "last_refresh": _last_refresh_status,
        "refresh_interval_minutes": REFRESH_INTERVAL,
        "scheduler_running": scheduler.running if scheduler else False,
    })


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(scheduled_refresh, "interval", minutes=REFRESH_INTERVAL, id="metabase_refresh")

_scheduler_started = False


def ensure_scheduler():
    """Start scheduler + initial refresh (idempotent, safe to call multiple times)."""
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    log.info("Refresh inicial ao iniciar o app...")
    scheduled_refresh()

    scheduler.start()
    log.info("Scheduler iniciado — refresh a cada %d minutos", REFRESH_INTERVAL)


def start_app(port=5050):
    """Start the app with initial refresh + scheduler. Used by launcher.py and __main__."""
    ensure_scheduler()
    host = os.getenv("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_app()
