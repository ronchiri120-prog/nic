"""
customers/documents.py
KYC document storage using AWS S3 with pre-signed URLs.

Supports:
  - National ID (front + back)
  - Passport photo
  - Proof of income (payslip/bank statement)
  - Logbook / title deed
  - Guarantor documents

When USE_S3=False (dev), files are stored locally in MEDIA_ROOT.
When USE_S3=True, files go to S3 with signed URL access (no public URLs).
"""
import os
import uuid
import mimetypes
from datetime import timedelta
from django.conf import settings
from django.utils import timezone


ALLOWED_TYPES = {
    'image/jpeg', 'image/png', 'image/webp',
    'application/pdf',
}

DOCUMENT_CATEGORIES = [
    ('ID_FRONT',     'National ID — Front'),
    ('ID_BACK',      'National ID — Back'),
    ('PASSPORT_PHOTO','Passport Photo'),
    ('PAYSLIP',       'Payslip / Pay Advice'),
    ('BANK_STATEMENT','Bank Statement'),
    ('LOGBOOK',       'Vehicle Logbook'),
    ('TITLE_DEED',    'Land Title Deed'),
    ('GUARANTOR_ID',  'Guarantor ID'),
    ('OTHER',         'Other Document'),
]

MAX_FILE_SIZE_MB = 10


def _s3_client():
    import boto3
    return boto3.client(
        's3',
        aws_access_key_id     = settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
        region_name           = getattr(settings, 'AWS_S3_REGION_NAME', 'af-south-1'),
    )


def generate_upload_url(customer_id: int, category: str, filename: str, content_type: str) -> dict:
    """
    Generate a pre-signed S3 PUT URL for direct browser-to-S3 upload.
    Returns the URL and the S3 key for storing in the database.
    """
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f'File type {content_type} not allowed. Allowed: {ALLOWED_TYPES}')

    ext    = os.path.splitext(filename)[1].lower() or '.bin'
    s3_key = f'kyc/{customer_id}/{category}/{uuid.uuid4().hex}{ext}'
    bucket = settings.AWS_STORAGE_BUCKET_NAME

    use_s3 = getattr(settings, 'USE_S3', False)
    if not use_s3:
        # Dev mode — return a local upload URL
        return {
            'upload_url':   f'/api/v1/customers/upload-local/?key={s3_key}',
            's3_key':       s3_key,
            'expires_in':   300,
            'method':       'PUT',
            'content_type': content_type,
            'dev_mode':     True,
        }

    s3 = _s3_client()
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket':      bucket,
            'Key':         s3_key,
            'ContentType': content_type,
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'customer-id': str(customer_id),
                'category':    category,
                'uploaded-at': timezone.now().isoformat(),
            },
        },
        ExpiresIn=300,  # 5 minutes to upload
    )
    return {
        'upload_url':   url,
        's3_key':       s3_key,
        'expires_in':   300,
        'method':       'PUT',
        'content_type': content_type,
    }


def generate_download_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """
    Generate a pre-signed S3 GET URL for secure document viewing.
    URLs expire after expiry_seconds (default 1 hour).
    """
    use_s3 = getattr(settings, 'USE_S3', False)
    if not use_s3:
        return f'/media/{s3_key}'

    s3  = _s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': s3_key},
        ExpiresIn=expiry_seconds,
    )


def delete_document(s3_key: str) -> bool:
    """Permanently delete a document from S3."""
    use_s3 = getattr(settings, 'USE_S3', False)
    if not use_s3:
        local_path = os.path.join(settings.MEDIA_ROOT, s3_key)
        if os.path.exists(local_path):
            os.remove(local_path)
        return True
    try:
        _s3_client().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
        return True
    except Exception:
        return False
