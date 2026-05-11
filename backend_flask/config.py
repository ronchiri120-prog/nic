"""config.py — Flask configuration for all environments."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Core ─────────────────────────────────────────────────────────────────
    SECRET_KEY           = os.getenv('SECRET_KEY', 'change-me-in-production')
    DEBUG                = False
    TESTING              = False

    # ── Database ─────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER','postgres')}:"
        f"{os.getenv('DB_PASSWORD','')}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5432')}/"
        f"{os.getenv('DB_NAME','quicklender_db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size':    10,
        'max_overflow': 20,
        'pool_pre_ping': True,
    }

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY              = os.getenv('SECRET_KEY', 'change-me')
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES   = timedelta(days=30)
    JWT_BLACKLIST_ENABLED       = True
    JWT_BLACKLIST_TOKEN_CHECKS  = ['access', 'refresh']

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # ── Mail ─────────────────────────────────────────────────────────────────
    MAIL_SERVER    = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    MAIL_PORT      = int(os.getenv('EMAIL_PORT', 587))
    MAIL_USE_TLS   = True
    MAIL_USERNAME  = os.getenv('EMAIL_HOST_USER', '')
    MAIL_PASSWORD  = os.getenv('EMAIL_HOST_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('EMAIL_HOST_USER', 'noreply@quicklender.co.ke')

    # ── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL         = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND     = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_TIMEZONE           = 'Africa/Nairobi'
    CELERY_ENABLE_UTC         = False

    # ── M-Pesa ───────────────────────────────────────────────────────────────
    MPESA_CONSUMER_KEY    = os.getenv('MPESA_CONSUMER_KEY', '')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
    MPESA_SHORTCODE       = os.getenv('MPESA_SHORTCODE', '174379')
    MPESA_PASSKEY         = os.getenv('MPESA_PASSKEY', '')
    MPESA_CALLBACK_URL    = os.getenv('MPESA_CALLBACK_URL', '')
    MPESA_ENV             = os.getenv('MPESA_ENV', 'sandbox')

    # ── Africa's Talking ─────────────────────────────────────────────────────
    AT_API_KEY   = os.getenv('AT_API_KEY', '')
    AT_USERNAME  = os.getenv('AT_USERNAME', 'sandbox')
    AT_SENDER_ID = os.getenv('AT_SENDER_ID', 'QuickLndr')

    # ── Encryption ───────────────────────────────────────────────────────────
    FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')

    # ── AWS S3 (KYC documents) ───────────────────────────────────────────────
    AWS_ACCESS_KEY_ID     = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET    = os.getenv('AWS_STORAGE_BUCKET', '')
    AWS_REGION            = os.getenv('AWS_REGION', 'af-south-1')

    # ── Static files (WhiteNoise) ─────────────────────────────────────────────
    STATIC_FOLDER  = 'static'
    STATIC_URL_PATH = '/static'

    # ── Login rate limiting ───────────────────────────────────────────────────
    LOGIN_MAX_ATTEMPTS  = 5
    LOGIN_LOCKOUT_SECS  = 900  # 15 minutes


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True to log all SQL


class ProductionConfig(Config):
    DEBUG = False
    # Force HTTPS
    SESSION_COOKIE_SECURE   = True
    REMEMBER_COOKIE_SECURE  = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
