"""WSGI entry point for gunicorn. Starts the scheduler before serving."""
from app import app, ensure_scheduler

ensure_scheduler()
