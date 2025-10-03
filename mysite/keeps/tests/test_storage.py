"""Tests for media storage backend."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.conf import settings
from django.test import override_settings
from keeps.storage import (
    MediaStorageBackend,
    MinIOStorageBackend,
    get_storage_backend
)


class TestMediaStorageBackend:
    """Test abstract MediaStorageBackend base class."""
    
    def test_generate_storage_key_with_uuid(self):
        """Test storage key generation with UUID."""
        backend = MediaStorageBackend()
        key = backend.generate_storage_key('test.jpg')
        
        assert key.startswith('keeps/')
        assert key.endswith('.jpg')
        assert len(key.split('/')) == 4  # keeps/year/month/day/filename
    
    def test_generate_storage_key_with_hash(self):
        """Test storage key generation with content hash."""
        backend = MediaStorageBackend()
        content_hash = 'a' * 64  # SHA-256 hash length
        
        key = backend.generate_storage_key('test.jpg', content_hash)
        
        assert key.startswith('keeps/')
        assert key.endswith('.jpg')
        assert 'aaaaaaaaaaaaaaaa' in key  # First 16 chars of hash
    
    def test_generate_storage_key_preserves_extension(self):
        """Test that file extension is preserved."""
        backend = MediaStorageBackend()
        
        for ext in ['.jpg', '.png', '.mp4', '.PDF']:
            key = backend.generate_storage_key(f'test{ext}')
            assert key.endswith(ext.lower())
    
    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        backend = MediaStorageBackend()
        content = b'test content'
        
        hash1 = backend.calculate_content_hash(content)
        hash2 = backend.calculate_content_hash(content)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars
        
        # Different content should produce different hash
        hash3 = backend.calculate_content_hash(b'different content')
        assert hash1 != hash3


@pytest.mark.django_db
class TestMinIOStorageBackend:
    """Test MinIOStorageBackend."""
    
    @patch('keeps.storage.Minio')
    def test_initialization(self, mock_minio_class):
        """Test MinIO backend initialization."""
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test_access',
            MINIO_SECRET_KEY='test_secret',
            MINIO_BUCKET_NAME='test-bucket',
            MINIO_USE_SSL=False
        ):
            backend = MinIOStorageBackend()
            
            assert backend.client == mock_client
            assert backend.endpoint == 'localhost:9000'
            assert backend.bucket_name == 'test-bucket'
            mock_client.bucket_exists.assert_called_once()
    
    @patch('keeps.storage.Minio')
    def test_ensure_bucket_exists(self, mock_minio_class):
        """Test bucket creation if it doesn't exist."""
        mock_client = Mock()
        mock_client.bucket_exists.return_value = False
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            mock_client.make_bucket.assert_called_once_with('test-bucket')
    
    @patch('keeps.storage.Minio')
    def test_save_file(self, mock_minio_class):
        """Test saving file to MinIO."""
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            file_content = b'test file content'
            
            storage_key = backend.save(file_content, 'test.jpg', 'image/jpeg')
            
            assert storage_key.startswith('keeps/')
            assert storage_key.endswith('.jpg')
            mock_client.put_object.assert_called_once()
            
            call_args = mock_client.put_object.call_args[1]
            assert call_args['bucket_name'] == 'test-bucket'
            assert call_args['object_name'] == storage_key
            assert call_args['length'] == len(file_content)
            assert call_args['content_type'] == 'image/jpeg'
    
    @patch('keeps.storage.Minio')
    def test_delete_file(self, mock_minio_class):
        """Test deleting file from MinIO."""
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            result = backend.delete('keeps/2024/01/01/test.jpg')
            
            assert result is True
            mock_client.remove_object.assert_called_once_with(
                'test-bucket',
                'keeps/2024/01/01/test.jpg'
            )
    
    @patch('keeps.storage.Minio')
    def test_get_url(self, mock_minio_class):
        """Test getting presigned URL."""
        mock_client = Mock()
        mock_client.presigned_get_object.return_value = 'http://presigned-url.com/file.jpg'
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            url = backend.get_url('keeps/2024/01/01/test.jpg', expires_in=7200)
            
            assert url == 'http://presigned-url.com/file.jpg'
            mock_client.presigned_get_object.assert_called_once()
    
    @patch('keeps.storage.Minio')
    def test_exists(self, mock_minio_class):
        """Test checking file existence."""
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            # File exists
            mock_client.stat_object.return_value = Mock()
            assert backend.exists('keeps/2024/01/01/test.jpg') is True
            
            # File doesn't exist
            from minio.error import S3Error
            backend.S3Error = S3Error
            mock_client.stat_object.side_effect = S3Error(
                code='NoSuchKey',
                message='Not found',
                resource='test',
                request_id='1',
                host_id='1',
                response=Mock(status=404)
            )
            assert backend.exists('keeps/2024/01/01/nonexistent.jpg') is False
    
    @patch('keeps.storage.Minio')
    def test_get_metadata(self, mock_minio_class):
        """Test getting file metadata."""
        mock_client = Mock()
        mock_stat = Mock()
        mock_stat.size = 1024
        mock_stat.content_type = 'image/jpeg'
        mock_stat.last_modified = datetime(2024, 1, 1)
        mock_stat.etag = 'abc123'
        mock_client.stat_object.return_value = mock_stat
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            metadata = backend.get_metadata('keeps/2024/01/01/test.jpg')
            
            assert metadata['size'] == 1024
            assert metadata['content_type'] == 'image/jpeg'
            assert metadata['etag'] == 'abc123'
            assert metadata['storage_backend'] == 'minio'
    
    @patch('keeps.storage.Minio')
    def test_get_file_content(self, mock_minio_class):
        """Test retrieving file content."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.read.return_value = b'file content'
        mock_client.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            
            content = backend.get_file_content('keeps/2024/01/01/test.jpg')
            
            assert content == b'file content'
            mock_client.get_object.assert_called_once()
            mock_response.close.assert_called_once()
    
    @patch('keeps.storage.Minio')
    def test_get_file_content_not_found(self, mock_minio_class):
        """Test retrieving non-existent file."""
        from minio.error import S3Error
        
        mock_client = Mock()
        mock_client.get_object.side_effect = S3Error(
            code='NoSuchKey',
            message='Not found',
            resource='test',
            request_id='1',
            host_id='1',
            response=Mock(status=404)
        )
        mock_minio_class.return_value = mock_client
        
        with override_settings(
            MINIO_ENDPOINT='http://localhost:9000',
            MINIO_ACCESS_KEY='test',
            MINIO_SECRET_KEY='test',
            MINIO_BUCKET_NAME='test-bucket'
        ):
            backend = MinIOStorageBackend()
            backend.S3Error = S3Error
            
            with pytest.raises(FileNotFoundError):
                backend.get_file_content('keeps/2024/01/01/nonexistent.jpg')


def test_get_storage_backend():
    """Test get_storage_backend function."""
    with patch('keeps.storage.MinIOStorageBackend') as mock_backend_class:
        mock_instance = Mock()
        mock_backend_class.return_value = mock_instance
        
        backend = get_storage_backend()
        
        assert backend == mock_instance
        mock_backend_class.assert_called_once()
