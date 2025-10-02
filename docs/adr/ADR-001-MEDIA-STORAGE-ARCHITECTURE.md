# ADR-001: Media Storage Architecture for TinyBeans

## Status
**Accepted** - *Date: 2024-12-28*

## Context

TinyBeans requires a robust media storage solution for family photos and videos uploaded as part of "keeps" (family memories). The system needs to:

1. **Handle large file uploads** efficiently without blocking the main application
2. **Support multiple storage backends** (local filesystem now, AWS S3 later)
3. **Provide secure access** to media files within family circles
4. **Scale horizontally** as the user base grows
5. **Maintain data integrity** and provide backup/recovery options
6. **Process media files** (thumbnails, compression, metadata extraction)

### Current State
- Django FileField storing files directly to local filesystem
- Synchronous uploads blocking request threads
- No abstraction layer for storage backends
- Limited media processing capabilities

### Requirements
- **Immediate**: Asynchronous upload processing with local storage
- **Future**: Easy migration to cloud storage (AWS S3)
- **Always**: Secure access control, data integrity, scalability

## Decision

We will implement a **pluggable media storage architecture** with the following components:

### 1. Storage Backend Abstraction
- **Storage interface** defining common operations (save, delete, get_url, exists)
- **Local storage backend** for development and initial deployment
- **S3-compatible backend** for future cloud migration
- **Configuration-driven selection** between backends

### 2. Asynchronous Upload Processing
- **Celery tasks** for file upload, processing, and storage operations
- **Upload staging area** for temporary file handling
- **Background processing** for thumbnails, compression, virus scanning
- **Upload progress tracking** and user notifications

### 3. S3-Compatible Local Development
- **MinIO** container for S3-compatible local development
- **Consistent API** between local and cloud environments
- **Easy testing** of S3 functionality locally

### 4. Media Processing Pipeline
- **File validation** (type, size, format)
- **Thumbnail generation** for photos
- **Video processing** (thumbnails, compression)
- **Metadata extraction** (EXIF data, duration, dimensions)
- **Security scanning** (virus detection, content analysis)

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │    │   Django API     │    │  Celery Worker  │
│                 │    │                  │    │                 │
│ Upload Request  │───▶│ Create Upload    │───▶│ Process Media   │
│                 │    │ Record           │    │                 │
│                 │    │                  │    │ ┌─────────────┐ │
│                 │    │                  │    │ │  Storage    │ │
│                 │    │                  │    │ │  Backend    │ │
│                 │    │                  │    │ │             │ │
│ Progress Check  │◀───│ Upload Status    │◀───│ │ ┌─────────┐ │ │
│                 │    │                  │    │ │ │ Local   │ │ │
│                 │    │                  │    │ │ │ or S3   │ │ │
│                 │    │                  │    │ │ └─────────┘ │ │
│                 │    │                  │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Implementation Plan

### Phase 1: Core Infrastructure (Immediate)
1. **Storage backend interface** and local implementation
2. **Celery task structure** for async processing
3. **Upload model** for tracking upload state
4. **MinIO container** for S3-compatible local testing

### Phase 2: Processing Pipeline
1. **File validation** and type detection
2. **Thumbnail generation** for images
3. **Video processing** capabilities
4. **Progress tracking** and notifications

### Phase 3: S3 Integration
1. **AWS S3 backend** implementation
2. **Migration tools** for moving from local to S3
3. **CDN integration** for optimized delivery
4. **Backup and recovery** procedures

### Phase 4: Advanced Features
1. **Content analysis** and auto-tagging
2. **Duplicate detection** and deduplication
3. **Advanced security** scanning
4. **Analytics and monitoring**

## Storage Backend Interface

```python
class MediaStorageBackend:
    def save(self, file_path: str, file_content: bytes) -> str:
        """Save file and return storage key"""
        
    def delete(self, storage_key: str) -> bool:
        """Delete file from storage"""
        
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Get signed URL for file access"""
        
    def exists(self, storage_key: str) -> bool:
        """Check if file exists"""
        
    def get_metadata(self, storage_key: str) -> dict:
        """Get file metadata (size, type, etc.)"""
```

## Local Development Setup

### MinIO (S3-Compatible Object Storage)
```yaml
# docker-compose.yml addition
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "9000:9000"  # API
    - "9001:9001"  # Console
  volumes:
    - minio_data:/data

minio-init:
  image: minio/mc:latest
  depends_on:
    - minio
  entrypoint: >
    /bin/sh -c "
    /usr/bin/mc alias set myminio http://minio:9000 minioadmin minioadmin;
    /usr/bin/mc mb myminio/tinybeans-media;
    /usr/bin/mc policy set public myminio/tinybeans-media;
    "
```

## Configuration Strategy

### Environment-Based Backend Selection
```python
# settings.py
MEDIA_STORAGE_BACKEND = os.environ.get('MEDIA_STORAGE_BACKEND', 'local')
MEDIA_STORAGE_SETTINGS = {
    'local': {
        'root_path': os.path.join(BASE_DIR, 'media'),
        'base_url': '/media/',
    },
    's3': {
        'bucket_name': os.environ.get('AWS_STORAGE_BUCKET_NAME'),
        'region': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
        'access_key': os.environ.get('AWS_ACCESS_KEY_ID'),
        'secret_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
    },
    'minio': {
        'endpoint': os.environ.get('MINIO_ENDPOINT', 'http://minio:9000'),
        'access_key': os.environ.get('MINIO_ACCESS_KEY', 'minioadmin'),
        'secret_key': os.environ.get('MINIO_SECRET_KEY', 'minioadmin'),
        'bucket_name': os.environ.get('MINIO_BUCKET_NAME', 'tinybeans-media'),
    }
}
```

## Security Considerations

### Access Control
- **Signed URLs** for time-limited access to media files
- **Circle membership validation** before generating access URLs
- **IP restrictions** and rate limiting for media endpoints

### File Validation
- **MIME type validation** to prevent malicious uploads
- **File size limits** to prevent abuse
- **Virus scanning** for uploaded files
- **Content analysis** to detect inappropriate content

### Data Protection
- **Encryption at rest** for sensitive media files
- **Secure transmission** (HTTPS/TLS) for all media operations
- **Access logging** for audit trails
- **Backup encryption** for stored backups

## Migration Strategy

### Local to S3 Migration
```python
# Migration task
def migrate_media_to_s3():
    local_backend = LocalStorageBackend()
    s3_backend = S3StorageBackend()
    
    for media_file in KeepMedia.objects.all():
        if local_backend.exists(media_file.storage_key):
            file_content = local_backend.read(media_file.storage_key)
            new_key = s3_backend.save(media_file.storage_key, file_content)
            media_file.storage_key = new_key
            media_file.storage_backend = 's3'
            media_file.save()
            local_backend.delete(media_file.storage_key)
```

## Monitoring and Observability

### Metrics to Track
- **Upload success/failure rates**
- **Processing time** for different file types/sizes
- **Storage usage** and costs
- **Access patterns** and performance

### Alerting
- **Failed uploads** requiring retry
- **Storage quota** approaching limits
- **Processing delays** beyond SLA
- **Security incidents** (failed access attempts)

## Testing Strategy

### Unit Tests
- **Storage backend implementations**
- **Celery task functions**
- **File validation logic**
- **Access control mechanisms**

### Integration Tests
- **End-to-end upload workflows**
- **Cross-backend compatibility**
- **Failure scenarios** and recovery
- **Performance under load**

### Load Testing
- **Concurrent upload handling**
- **Large file processing**
- **Storage backend scalability**
- **Celery worker performance**

## Benefits

### Immediate
- **Non-blocking uploads** improve user experience
- **Scalable architecture** supports growth
- **Local development** with S3 compatibility
- **Robust error handling** and recovery

### Long-term
- **Easy cloud migration** when needed
- **Advanced processing** capabilities
- **Cost optimization** through tiered storage
- **Enhanced security** and compliance

## Trade-offs

### Complexity vs. Flexibility
- **Added complexity** in system architecture
- **More moving parts** to monitor and maintain
- **Greater flexibility** for future requirements
- **Easier testing** with abstracted backends

### Performance vs. Features
- **Async processing** may delay immediate availability
- **Rich processing** capabilities for better UX
- **Configurable trade-offs** based on use case

## Alternatives Considered

### Direct S3 Upload
- **Pros**: Simpler, direct to cloud
- **Cons**: Vendor lock-in, harder local development, limited processing

### Synchronous Processing
- **Pros**: Immediate availability, simpler flow
- **Cons**: Blocking requests, poor scalability, timeout issues

### Third-party Services (Cloudinary, etc.)
- **Pros**: Full-featured, managed service
- **Cons**: Higher costs, vendor dependency, less control

## Conclusion

The pluggable media storage architecture provides the right balance of **immediate functionality** and **future flexibility**. Starting with local storage and MinIO for development allows rapid iteration while building the foundation for cloud migration when needed.

The async processing pipeline ensures **scalability** and **user experience** while the storage abstraction provides **portability** and **testability**.

This decision supports TinyBeans' growth trajectory while maintaining development velocity and operational simplicity.