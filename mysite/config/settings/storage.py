"""Media storage and file upload configuration"""
import os


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
