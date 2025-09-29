"""Media storage backend interface and MinIO implementation.

This module provides MinIO-based storage for media files with support
for thumbnails, gallery images, and full-size originals.
"""
import os
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urljoin
import mimetypes
import hashlib
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


class MediaStorageBackend(ABC):
    """Abstract base class for media storage backends."""
    
    @abstractmethod
    def save(self, file_content: bytes, filename: str, content_type: str = None) -> str:
        """Save file content and return storage key."""
        pass
    
    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get URL for file access."""
        pass
    
    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists in storage."""
        pass
    
    @abstractmethod
    def get_metadata(self, storage_key: str) -> Dict[str, Any]:
        """Get file metadata."""
        pass
    
    def generate_storage_key(self, filename: str, content_hash: str = None) -> str:
        """Generate unique storage key for file."""
        now = timezone.now()
        date_path = now.strftime('%Y/%m/%d')
        
        # Use content hash if provided, otherwise generate UUID
        if content_hash:
            unique_id = content_hash[:16]
        else:
            unique_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        # Preserve file extension
        name, ext = os.path.splitext(filename)
        safe_filename = f"{unique_id}{ext.lower()}"
        
        return f"keeps/{date_path}/{safe_filename}"
    
    def calculate_content_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()


class MinIOStorageBackend(MediaStorageBackend):
    """MinIO (S3-compatible) storage backend."""
    
    def __init__(self):
        try:
            from minio import Minio
            from minio.error import S3Error
            self.S3Error = S3Error
        except ImportError:
            raise ImportError("minio package is required for MinIO backend")
        
        self.endpoint = settings.MINIO_ENDPOINT.replace('http://', '').replace('https://', '')
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.secure = getattr(settings, 'MINIO_USE_SSL', False)
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except self.S3Error:
            pass  # Bucket might already exist
    
    def save(self, file_content: bytes, filename: str, content_type: str = None) -> str:
        """Save file to MinIO."""
        from io import BytesIO
        
        content_hash = self.calculate_content_hash(file_content)
        storage_key = self.generate_storage_key(filename, content_hash)
        
        # Upload to MinIO
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=storage_key,
            data=BytesIO(file_content),
            length=len(file_content),
            content_type=content_type or 'application/octet-stream'
        )
        
        return storage_key
    
    def get_file_content(self, storage_key: str) -> bytes:
        """Get file content from MinIO."""
        try:
            response = self.client.get_object(self.bucket_name, storage_key)
            return response.read()
        except self.S3Error:
            raise FileNotFoundError(f"File not found: {storage_key}")
        finally:
            if 'response' in locals():
                response.close()
    
    def delete(self, storage_key: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket_name, storage_key)
            return True
        except self.S3Error:
            return False
    
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get presigned URL for MinIO file access."""
        from datetime import timedelta
        
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=storage_key,
                expires=timedelta(seconds=expires_in)
            )
            return url
        except self.S3Error:
            return None
    
    def exists(self, storage_key: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            self.client.stat_object(self.bucket_name, storage_key)
            return True
        except self.S3Error:
            return False
    
    def get_metadata(self, storage_key: str) -> Dict[str, Any]:
        """Get file metadata from MinIO."""
        try:
            stat = self.client.stat_object(self.bucket_name, storage_key)
            return {
                'size': stat.size,
                'content_type': stat.content_type,
                'modified': stat.last_modified,
                'etag': stat.etag,
                'storage_backend': 'minio',
            }
        except self.S3Error:
            return {}


def get_storage_backend() -> MediaStorageBackend:
    """Get the MinIO storage backend instance."""
    return MinIOStorageBackend()