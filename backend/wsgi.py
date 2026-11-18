"""Production entry point: gunicorn wsgi:app (use ONE worker so only one monitor thread runs)."""
import os

from app import create_app

app = create_app(start_background=True, interval=int(os.environ.get("CHECK_INTERVAL", "30")))
