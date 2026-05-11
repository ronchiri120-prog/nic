"""
Gunicorn production configuration for QuickLender.
Usage: gunicorn -c deployment/gunicorn.conf.py quicklender_project.wsgi:application
"""
import multiprocessing
import os

# ─── Server socket ────────────────────────────────────
bind            = "127.0.0.1:8000"
backlog         = 2048

# ─── Workers ──────────────────────────────────────────
workers         = multiprocessing.cpu_count() * 2 + 1
worker_class    = "sync"       # Use "gevent" with: pip install gevent
worker_connections = 1000
threads         = 2            # Per worker (sync class ignores this, gthread uses it)
max_requests    = 1000         # Restart workers after N requests (prevents memory leaks)
max_requests_jitter = 100      # Spread restarts across workers
timeout         = 120          # Kill workers that take >120s
graceful_timeout= 30
keepalive       = 5

# ─── Logging ──────────────────────────────────────────
accesslog       = "/var/log/quicklender/gunicorn.access.log"
errorlog        = "/var/log/quicklender/gunicorn.error.log"
loglevel        = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ─── Process management ───────────────────────────────
daemon          = False        # Managed by systemd
pidfile         = "/var/run/quicklender/gunicorn.pid"
user            = "quicklender"
group           = "quicklender"
umask           = 0o007

# ─── Environment ──────────────────────────────────────
raw_env         = [
    "DJANGO_ENV=production",
    "DJANGO_SETTINGS_MODULE=quicklender_project.settings",
]

# ─── Hooks ────────────────────────────────────────────
def on_starting(server):
    server.log.info("QuickLender API starting up...")

def worker_abort(worker):
    worker.log.info(f"Worker {worker.pid} aborted")

def post_fork(server, worker):
    server.log.info(f"Worker {worker.pid} spawned")
