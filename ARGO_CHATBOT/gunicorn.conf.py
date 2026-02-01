# Gunicorn configuration for Railway deployment
import os

# Bind to PORT from environment (Railway sets this)
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Workers and threads (optimized for 512MB RAM)
workers = 2
threads = 2
worker_class = "gthread"

# Timeout for AI/DB queries
timeout = 120
graceful_timeout = 30
keepalive = 30

# Preload for shared DB connections
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
