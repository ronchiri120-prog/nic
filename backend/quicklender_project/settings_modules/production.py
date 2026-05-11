"""
QuickLender — Production Settings
Hardened for live deployment on Ubuntu/Debian with Nginx + Gunicorn.
"""
from .base import *

# ─── SECURITY ─────────────────────────────────────────
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

# HTTPS hardening
SECURE_HSTS_SECONDS            = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True
SECURE_SSL_REDIRECT            = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
SECURE_BROWSER_XSS_FILTER      = True
SECURE_CONTENT_TYPE_NOSNIFF    = True
X_FRAME_OPTIONS                = 'DENY'
SECURE_REFERRER_POLICY         = 'strict-origin-when-cross-origin'

# ─── CORS ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True

# ─── DATABASE — Production SSL ────────────────────────
DATABASES['default']['OPTIONS']['sslmode'] = config('DB_SSL_MODE', default='require')

# ─── EMAIL — SMTP Live ────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# ─── STATIC / MEDIA — AWS S3 ─────────────────────────
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID       = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY   = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME      = config('AWS_S3_REGION_NAME', default='af-south-1')
    AWS_S3_CUSTOM_DOMAIN    = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL           = 'private'
    AWS_S3_FILE_OVERWRITE     = False

    # Static files → S3/CloudFront
    STATICFILES_STORAGE    = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL             = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

    # Media files → S3 (private, signed URLs)
    DEFAULT_FILE_STORAGE   = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL              = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ─── CACHING — Redis ──────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ─── SENTRY — Error Monitoring ────────────────────────
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        traces_sample_rate=0.1,   # 10% of transactions
        profiles_sample_rate=0.05,
        send_default_pii=False,   # GDPR compliance
        environment='production',
        release=config('APP_VERSION', default='3.0.0'),
        before_send=_filter_sensitive_data,
    )

def _filter_sensitive_data(event, hint):
    """Strip sensitive fields from Sentry events."""
    for key in ('password', 'mpesa_passkey', 'api_key', 'secret'):
        if key in event.get('request', {}).get('data', {}):
            event['request']['data'][key] = '[REDACTED]'
    return event

# ─── THROTTLING — Tighter in production ───────────────
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '20/minute',
    'user': '120/minute',
    'login': '5/minute',
}

# ─── ADMIN URL ────────────────────────────────────────
ADMIN_URL = config('ADMIN_URL', default='ql-admin-secret/')

# ─── PRODUCTION LOGGING ───────────────────────────────
LOGGING['handlers']['syslog'] = {
    'class': 'logging.handlers.SysLogHandler',
    'address': '/dev/log',
    'formatter': 'verbose',
    'facility': 'local7',
}
LOGGING['root']['handlers'] = ['syslog', 'file']
