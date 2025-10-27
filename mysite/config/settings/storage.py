"""Media storage and file upload configuration"""
import os
from django.core.exceptions import ImproperlyConfigured


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


# Media Storage Configuration - MinIO Only
MEDIA_STORAGE_BACKEND = 'minio'

# MinIO Settings (S3-compatible object storage)
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'http://minio:9020')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME', 'tinybeans-media')
MINIO_USE_SSL = _env_flag('MINIO_USE_SSL', default=False)

# Media Upload Settings
MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 100 * 1024 * 1024))  # 100MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo']

# Image Processing Settings
IMAGE_SIZES = {
    'thumbnail': (150, 150),
    'gallery': (800, 600),
    'full': None,  # Original size
}


def _should_enforce_secure_storage() -> bool:
    environment = (os.environ.get('DJANGO_ENVIRONMENT') or '').lower()
    debug_flag = _env_flag('DJANGO_DEBUG', default=False)
    allow_insecure = _env_flag('DJANGO_ALLOW_INSECURE_MINIO', default=False)
    if allow_insecure:
        return False
    if debug_flag:
        return False
    return environment not in {'local', 'development', 'dev', 'test'}


if _should_enforce_secure_storage():
    if MINIO_ACCESS_KEY == 'minioadmin' or MINIO_SECRET_KEY == 'minioadmin':
        raise ImproperlyConfigured(
            'Override MINIO_ACCESS_KEY and MINIO_SECRET_KEY for non-local environments.'
        )
    if not MINIO_USE_SSL:
        raise ImproperlyConfigured(
            'Enable MINIO_USE_SSL (or set DJANGO_ALLOW_INSECURE_MINIO=1) for non-local environments.'
        )
    if MINIO_ENDPOINT.startswith('http://'):
        raise ImproperlyConfigured(
            'Use an HTTPS MINIO_ENDPOINT in non-local environments.'
        )
