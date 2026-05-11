# Gunicorn configuration file for QuickLender production deployment
# Usage: gunicorn -c gunicorn_config.py quicklender_project.wsgi:application

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Process naming
proc_name = 'quicklender'

# Logging
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Server mechanics
daemon = False
pidfile = 'gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if using HTTPS)
# keyfile = '/path/to/ssl/key.pem'
# certfile = '/path/to/ssl/cert.pem'

# Environment variables for production
raw_env = [
    'DJANGO_SETTINGS_MODULE=quicklender_project.settings',
]
