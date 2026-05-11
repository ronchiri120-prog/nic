"""
QuickLender — Base Settings (shared across all environments)
"""
import os
from pathlib import Path
from datetime import timedelta
# Celery schedules — imported lazily to avoid naming conflicts
try:
    from celery.schedules import crontab as _crontab
    def crontab(**kwargs): return _crontab(**kwargs)
except ImportError:
    # Celery not installed — beat schedules won't work but Django will start
    def crontab(**kwargs): return kwargs

BASE_DIR = Path(__file__).resolve().parent.parent.parent

try:
    from decouple import config
except ImportError:
    def config(key, default=None, cast=None):
        val = os.environ.get(key, default)
        return cast(val) if (cast and val is not None) else val

SECRET_KEY    = config('SECRET_KEY')
DEBUG         = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    # QuickLender
    'apps.accounts',
    'apps.customers',
    'apps.loans',
    'apps.payments',
    'apps.branches',
    'apps.reports',
    'apps.allocations',
    'apps.assets',
    'apps.notifications',
    'apps.groups',
    'apps.accounting',
    'apps.documents',
    'apps.crm',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF      = 'quicklender_project.urls'
WSGI_APPLICATION  = 'quicklender_project.wsgi.application'
AUTH_USER_MODEL   = 'accounts.User'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

# ── Database: SQLite for dev, PostgreSQL for production ──────────────────────
_use_sqlite = config('USE_SQLITE', default=False, cast=bool)

if _use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     config('DB_NAME',     default='quicklender_db'),
            'USER':     config('DB_USER',     default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Africa/Nairobi'
USE_I18N      = True
USE_TZ        = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL        = '/static/'
STATIC_ROOT       = BASE_DIR / 'staticfiles'     # collectstatic output dir
STATICFILES_DIRS  = []                           # extra dirs scanned by collectstatic
                                                  # (Django admin + DRF browsable API only)
                                                  # Frontend HTML/CSS/JS is served by nginx
MEDIA_URL    = '/media/'
MEDIA_ROOT   = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'anon': '30/minute', 'user': '200/minute'},
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN':        True,
    'ALGORITHM':                'HS256',
    'AUTH_HEADER_TYPES':        ('Bearer',),
}

CELERY_BROKER_URL        = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_TIMEZONE          = 'Africa/Nairobi'
CELERY_ENABLE_UTC        = False
CELERY_RESULT_EXTENDED   = True
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULE = {
    'daily-payment-reminders': {'task': 'notifications.daily_payment_reminders',    'schedule': crontab(hour=8,  minute=0)},
    'daily-overdue-chase':     {'task': 'notifications.daily_overdue_chase',         'schedule': crontab(hour=9,  minute=0)},
    'check-arrears-and-tier':  {'task': 'loans.check_arrears',                       'schedule': crontab(hour=9,  minute=5)},
    'weekly-portfolio-report': {'task': 'notifications.weekly_portfolio_report',     'schedule': crontab(hour=7,  minute=0, day_of_week=1)},
    'monthly-dormant-check':   {'task': 'notifications.mark_dormant_customers',      'schedule': crontab(hour=0,  minute=5, day_of_month=1)},
    'mpesa-reconcile':         {'task': 'notifications.reconcile_mpesa_transactions', 'schedule': crontab(minute='*/15')},
    'reset-loans-not-disbursed': {'task': 'loans.tasks.reset_loans_not_disbursed_by_noon', 'schedule': crontab(minute='*/1')},
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'QuickLender API', 'DESCRIPTION': 'Microfinance LMS REST API',
    'VERSION': '3.0.0', 'SERVE_INCLUDE_SCHEMA': False,
}

MPESA_CONSUMER_KEY    = config('MPESA_CONSUMER_KEY',    default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_SHORTCODE       = config('MPESA_SHORTCODE',       default='174379')
MPESA_PASSKEY         = config('MPESA_PASSKEY',         default='')
MPESA_CALLBACK_URL    = config('MPESA_CALLBACK_URL',    default='')
MPESA_ENV             = config('MPESA_ENV',             default='sandbox')

AT_API_KEY   = config('AT_API_KEY',   default='')
AT_USERNAME  = config('AT_USERNAME',  default='sandbox')
AT_SENDER_ID = config('AT_SENDER_ID', default='QuickLndr')

EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT',           default=587,  cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',        default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',      default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD',  default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',   default='QuickLender <noreply@quicklender.co.ke>')

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}', 'style': '{'},
        'simple':  {'format': '{levelname} {message}', 'style': '{'},
    },
    'filters': {'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}},
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file':    {'class': 'logging.handlers.RotatingFileHandler',
                    'filename': str(LOGS_DIR / 'quicklender.log'),
                    'maxBytes': 10 * 1024 * 1024,  # 10MB
                    'backupCount': 5, 'formatter': 'verbose'},
        'error_file': {'class': 'logging.handlers.RotatingFileHandler',
                       'filename': str(LOGS_DIR / 'errors.log'),
                       'maxBytes': 10 * 1024 * 1024, 'backupCount': 5,
                       'level': 'ERROR', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps': {'handlers': ['console', 'file', 'error_file'], 'level': 'DEBUG', 'propagate': False},
        'django.request': {'handlers': ['error_file'], 'level': 'ERROR', 'propagate': False},
        'celery': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}

# ─── PII Encryption ─────────────────────────────────
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent',
    'x-csrftoken', 'x-requested-with',
]


# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587,  cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='QuickLender <noreply@quicklender.co.ke>')

