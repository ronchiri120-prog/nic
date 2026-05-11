"""
QuickLender — Development Settings
"""
from .base import *

DEBUG = True
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only-key-never-use-in-production-xK9mP2')
ALLOWED_HOSTS = ['*']

# Simple in-memory cache for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Relaxed CORS for local dev
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Console email (prints to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar (optional)
INTERNAL_IPS = ['127.0.0.1']

# Faster password hashing in dev
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Relaxed throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/minute',
    'user': '1000/minute',
}

# Show SQL queries in dev
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG' if config('SHOW_SQL', default=False, cast=bool) else 'INFO',
    'propagate': False,
}
