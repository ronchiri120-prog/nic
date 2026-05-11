"""
accounts/totp.py
Two-factor authentication using TOTP (RFC 6238).
Compatible with Google Authenticator, Authy, 1Password.

Dependencies: pyotp (already in requirements via sentry-sdk deps — add explicitly)
"""
import pyotp
import secrets
import qrcode
import io
import base64
from django.conf import settings


ISSUER = getattr(settings, 'OTP_ISSUER', 'QuickLender')
WINDOW = 1   # Allow 1 step drift (30s each side)


def generate_totp_secret() -> str:
    """Generate a new base32 TOTP secret for a user."""
    return pyotp.random_base32()


def get_totp_uri(user_email: str, secret: str) -> str:
    """Build an otpauth:// URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name=ISSUER)


def get_qr_code_base64(user_email: str, secret: str) -> str:
    """Return a base64-encoded PNG of the QR code for the provisioning URI."""
    uri = get_totp_uri(user_email, secret)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, token: str) -> bool:
    """
    Verify a 6-digit TOTP token.
    Allows 1-step window to handle clock drift.
    """
    if not secret or not token:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(str(token).strip(), valid_window=WINDOW)
    except Exception:
        return False


def generate_backup_codes(count: int = 10) -> list[str]:
    """
    Generate one-time backup codes (for when phone is unavailable).
    Format: XXXX-XXXX (8 hex chars split with dash).
    """
    return [
        secrets.token_hex(4).upper() + '-' + secrets.token_hex(4).upper()
        for _ in range(count)
    ]
