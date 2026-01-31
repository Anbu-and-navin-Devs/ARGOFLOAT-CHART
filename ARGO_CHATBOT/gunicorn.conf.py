# Gunicorn configuration for Render deployment
# Optimized for CockroachDB + AI queries

# Timeout for worker processes (in seconds)
timeout = 120

# Number of worker processes (keep low for free tier - 512MB RAM)
workers = 2

# Threads per worker (better for I/O-bound DB queries)
threads = 2

# Worker class - use gthread for better concurrency with DB
worker_class = "gthread"

# Keep alive connections (longer to reuse connections)
keepalive = 30

# Preload app to share DB connections across workers
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Graceful timeout
graceful_timeout = 30

# Worker connections (for gthread)
worker_connections = 100

def on_starting(server):
    """Warm up database when Gunicorn starts."""
    pass

def post_fork(server, worker):
    """Initialize DB connection in each worker."""
    try:
        from app import warm_db_connection
        warm_db_connection()
    except Exception as e:
        print(f"Worker warm-up failed: {e}")
