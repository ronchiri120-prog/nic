"""
customers/encryption.py
Fernet symmetric encryption for PII fields.
Fields encrypted at rest: national_id, phone, email, guarantor_id, guarantor_phone.

Key management:
  - FIELD_ENCRYPTION_KEY in settings (32-byte base64 key)
  - Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  - Store in .env, never in code
  - Rotate with: python manage.py rotate_encryption_key --old-key=... --new-key=...

Architecture:
  - EncryptedField stores ciphertext prefixed with "enc:"
  - Plain values (no prefix) are migrated lazily on first read
  - Search is via HMAC index (deterministic but one-way)
"""
import base64
import hashlib
import hmac
import logging

logger = logging.getLogger('apps.customers')

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        from django.conf import settings
        from cryptography.fernet import Fernet
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            logger.warning('FIELD_ENCRYPTION_KEY not set — PII fields stored in plaintext')
            return None
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f'Invalid FIELD_ENCRYPTION_KEY: {e}')
            return None
    return _fernet


def encrypt(value: str) -> str:
    """Encrypt a string. Returns 'enc:<ciphertext>' or plain if no key set."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value  # Graceful degradation
    ciphertext = f.encrypt(value.encode()).decode()
    return f'enc:{ciphertext}'


def decrypt(value: str) -> str:
    """Decrypt a string. Returns plaintext. Handles unencrypted values gracefully."""
    if not value:
        return value
    if not value.startswith('enc:'):
        return value  # Plain value (legacy or encryption disabled)
    f = _get_fernet()
    if f is None:
        return value[4:]  # Strip prefix, return raw ciphertext as fallback
    try:
        return f.decrypt(value[4:].encode()).decode()
    except Exception:
        logger.warning(f'Decryption failed for value starting with {value[:12]}...')
        return ''


def hmac_index(value: str) -> str:
    """
    Create a deterministic HMAC of a value for use as a search index.
    Allows exact-match search without decrypting all rows.
    """
    if not value:
        return ''
    from django.conf import settings
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', 'default-search-key')
    h = hmac.new(key.encode(), value.lower().encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()[:32]


class EncryptedField:
    """
    Descriptor for transparent encryption/decryption on model instances.

    Usage in models.py:
        national_id = models.CharField(max_length=500)  # stores ciphertext
        _national_id = EncryptedField('national_id')

    Then access via: customer._national_id (decrypts automatically)
    """
    def __init__(self, field_name: str):
        self.field_name = field_name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        raw = getattr(obj, self.field_name, None)
        return decrypt(raw) if raw else raw

    def __set__(self, obj, value):
        setattr(obj, self.field_name, encrypt(value) if value else value)
