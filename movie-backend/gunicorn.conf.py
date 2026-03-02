# Gunicorn configuration for Render deployment
# The startup downloads IMDb datasets and builds TF-IDF index,
# which can take several minutes — we need a generous timeout.

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1  # Free tier has limited RAM (512MB), 1 worker is safer
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 300  # 5 minutes — enough for IMDb download + DB build + TF-IDF index
graceful_timeout = 120
preload_app = False  # Don't preload — let each worker run its own startup event
accesslog = "-"
errorlog = "-"
loglevel = "info"
