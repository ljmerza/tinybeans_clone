# ADR-002: Media Storage Architecture for Keeps

## Status
Accepted

## Context

The Tinybeans application needs to store and serve media files (photos and videos) associated with family memories ("keeps"). We need a solution that:

1. Handles large files efficiently (photos up to 20MB, videos up to 100MB)
2. Supports multiple file formats (JPEG, PNG, GIF, WebP for images; MP4, MOV, AVI, WebM for videos)
3. Automatically generates thumbnails and multiple sizes for photos
4. Provides secure access with expiring URLs
5. Scales from local development to cloud production
6. Allows easy migration between storage backends

## Decision

We will implement a pluggable storage architecture using MinIO for development/staging and AWS S3 for production, with the following components:

### Storage Backend Architecture

```
┌─────────────────────────────────────┐
│           Django Views              │
├─────────────────────────────────────┤
│         Celery Workers              │
│   ┌─────────────────────────────┐   │
│   │    Media Processing         │   │
│   │  - Validation               │   │
│   │  - Thumbnail Generation     │   │
│   │  - Multi-size Creation      │   │
│   └─────────────────────────────┘   │
├─────────────────────────────────────┤
│      Storage Backend Interface     │
│   ┌─────────────┬─────────────────┐ │
│   │ MinIO       │ AWS S3          │ │
│   │ Backend     │ Backend         │ │
│   └─────────────┴─────────────────┘ │
└─────────────────────────────────────┘
```

### Storage Backend Interface

```python
class StorageBackend:
    def store(self, file_path: str, storage_key: str) -> bool
    def get_url(self, storage_key: str, expires_in: int = 3600) -> str
    def delete(self, storage_key: str) -> bool
    def exists(self, storage_key: str) -> bool
```

### File Organization

Files are organized with the following key structure:
```
keeps/
├── originals/
│   ├── YYYY/MM/DD/
│   │   └── {uuid}.{ext}
├── thumbnails/
│   ├── YYYY/MM/DD/
│   │   └── {uuid}_thumb.{ext}
└── gallery/
    ├── YYYY/MM/DD/
    │   └── {uuid}_gallery.{ext}
```

### Media Processing Pipeline

1. **Upload Phase**:
   - File uploaded via multipart form
   - Saved to temporary location
   - Upload record created with `pending` status
   - Celery task queued for processing

2. **Validation Phase**:
   - File type validation
   - Size validation
   - Virus scanning (future)
   - Status updated to `validating`

3. **Processing Phase**:
   - Status updated to `processing`
   - Original file stored
   - For photos: Generate thumbnail (150x150) and gallery (800x600) versions
   - For videos: Store as-is (processing deferred)
   - KeepMedia record created
   - Status updated to `completed`

4. **Error Handling**:
   - On any failure, status set to `failed`
   - Error message stored
   - Temporary files cleaned up
   - User notified of failure

## Implementation Details

### MinIO Configuration (Development/Staging)

MinIO provides S3-compatible object storage that runs locally:

```yaml
# docker-compose.yml
minio:
  image: minio/minio:RELEASE.2024-09-13T20-26-02Z
  command: server /data --console-address ":9001"
  environment:
    - MINIO_ROOT_USER=tinybeans
    - MINIO_ROOT_PASSWORD=tinybeans123
  ports:
    - "9000:9000"
    - "9001:9001"
  volumes:
    - minio_data:/data

minio-init:
  image: minio/mc:RELEASE.2024-09-13T20-26-02Z
  depends_on:
    - minio
  entrypoint: >
    /bin/sh -c "
    until (/usr/bin/mc config host add myminio http://minio:9000 tinybeans tinybeans123) do echo '...waiting...' && sleep 1; done;
    /usr/bin/mc mb myminio/tinybeans-media;
    /usr/bin/mc policy set public myminio/tinybeans-media;
    echo 'MinIO bucket setup complete'
    "
```

### Django Settings

```python
# Media storage settings
MEDIA_STORAGE_BACKEND = env('MEDIA_STORAGE_BACKEND', default='minio')

# MinIO settings
MINIO_ENDPOINT = env('MINIO_ENDPOINT', default='localhost:9000')
MINIO_ACCESS_KEY = env('MINIO_ACCESS_KEY', default='tinybeans')
MINIO_SECRET_KEY = env('MINIO_SECRET_KEY', default='tinybeans123')
MINIO_BUCKET_NAME = env('MINIO_BUCKET_NAME', default='tinybeans-media')
MINIO_USE_HTTPS = env.bool('MINIO_USE_HTTPS', default=False)

# AWS S3 settings (production)
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')

# File upload limits
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_IMAGE_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
]
ALLOWED_VIDEO_TYPES = [
    'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'
]

# Thumbnail settings
THUMBNAIL_SIZE = (150, 150)
GALLERY_SIZE = (800, 600)
THUMBNAIL_QUALITY = 85
```

### Database Models

```python
class KeepMedia(models.Model):
    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='media_files')
    media_type = models.CharField(max_length=10, choices=[('photo', 'Photo'), ('video', 'Video')])
    
    # Storage keys for different sizes
    storage_key_original = models.CharField(max_length=500)
    storage_key_thumbnail = models.CharField(max_length=500, blank=True)
    storage_key_gallery = models.CharField(max_length=500, blank=True)
    
    # File metadata
    file_size = models.PositiveIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Processing flags
    thumbnails_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

class MediaUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='uploads')
    media_type = models.CharField(max_length=10, choices=[('photo', 'Photo'), ('video', 'Video')])
    
    # Upload metadata
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    temp_file_path = models.CharField(max_length=500)
    
    # Processing status
    status = models.CharField(max_length=20, choices=MediaUploadStatus.choices, default=MediaUploadStatus.PENDING)
    error_message = models.TextField(blank=True)
    
    # Relationship to final media file
    media_file = models.ForeignKey(KeepMedia, on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
```

### Celery Tasks

```python
@celery_app.task(bind=True, max_retries=3)
def validate_media_file(self, upload_id: str):
    try:
        upload = MediaUpload.objects.get(id=upload_id)
        upload.status = MediaUploadStatus.VALIDATING
        upload.save()
        
        # Validate file
        validate_file_type(upload.temp_file_path, upload.content_type)
        validate_file_size(upload.temp_file_path, upload.file_size)
        
        # Process file
        upload.status = MediaUploadStatus.PROCESSING
        upload.save()
        
        storage = get_storage_backend()
        
        # Store original file
        original_key = generate_storage_key(upload, 'original')
        storage.store(upload.temp_file_path, original_key)
        
        # Create KeepMedia record
        media = KeepMedia.objects.create(
            keep=upload.keep,
            media_type=upload.media_type,
            storage_key_original=original_key,
            file_size=upload.file_size,
            original_filename=upload.original_filename,
            content_type=upload.content_type,
        )
        
        # Generate thumbnails for photos
        if upload.media_type == 'photo':
            generate_thumbnails.delay(str(media.id))
        
        # Link upload to media file
        upload.media_file = media
        upload.status = MediaUploadStatus.COMPLETED
        upload.save()
        
        # Clean up temp file
        os.remove(upload.temp_file_path)
        
    except Exception as exc:
        upload.status = MediaUploadStatus.FAILED
        upload.error_message = str(exc)
        upload.save()
        
        # Clean up temp file
        if os.path.exists(upload.temp_file_path):
            os.remove(upload.temp_file_path)
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
```

## Migration Strategy

### Phase 1: MinIO Development (Current)
- Implement MinIO backend for local development
- Test upload, processing, and serving workflows
- Validate thumbnail generation and multi-size storage

### Phase 2: AWS S3 Production
- Implement AWS S3 backend with same interface
- Test S3 integration in staging environment
- Configure CloudFront CDN for fast global delivery

### Phase 3: Migration Tools
- Create management commands for data migration
- Implement background sync between storage backends
- Add monitoring and validation tools

## Security Considerations

1. **Access Control**: All media URLs expire after 1 hour and require authentication
2. **File Validation**: Strict file type and size validation before processing
3. **Virus Scanning**: Future integration with ClamAV or cloud-based scanning
4. **Content Policy**: Automated content moderation for inappropriate material (future)

## Performance Considerations

1. **Async Processing**: All file processing happens asynchronously via Celery
2. **CDN Integration**: CloudFront for S3, nginx for MinIO
3. **Caching**: Media URLs cached for 1 hour, metadata cached for 5 minutes
4. **Optimization**: Images automatically optimized for web delivery

## Monitoring and Alerting

1. **Upload Metrics**: Track upload success/failure rates
2. **Processing Time**: Monitor thumbnail generation performance
3. **Storage Usage**: Track storage consumption and costs
4. **Error Alerting**: Slack notifications for processing failures

## Cost Implications

### Development/Staging (MinIO)
- Infrastructure cost: ~$0 (runs on existing servers)
- Storage cost: Local disk storage only

### Production (AWS S3)
- Storage cost: ~$0.023/GB/month for standard storage
- Transfer cost: ~$0.09/GB for outbound transfer
- Request cost: ~$0.0004/1000 GET requests
- CloudFront: ~$0.085/GB for first 10TB/month

Estimated monthly cost for 1000 active families:
- Storage (100GB): $2.30
- Transfer (500GB): $45.00
- Requests (1M): $0.40
- CloudFront (500GB): $42.50
- **Total: ~$90/month**

## Alternatives Considered

1. **Django File Storage**: Too limited for multi-size generation and cloud storage
2. **Direct S3 Upload**: Complex client-side handling, no server-side validation
3. **Local File Storage**: No scalability, backup complexity
4. **Cloudinary**: Expensive for high-volume usage, vendor lock-in

## Consequences

### Positive
- Scalable architecture that grows with the application
- Consistent interface allows easy backend switching
- Async processing prevents UI blocking
- Cost-effective for expected usage levels
- Strong security and access control

### Negative
- Additional complexity in deployment (MinIO service)
- Async processing adds complexity to error handling
- Storage costs will scale with usage
- Migration between backends requires careful planning

## Decision Date
2023-12-01

## Reviewers
- Development Team
- Infrastructure Team