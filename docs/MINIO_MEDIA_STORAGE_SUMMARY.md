# MinIO-Based Media Storage Implementation Summary

## Overview
Simplified the media storage architecture to use **MinIO exclusively** for now, with easy migration path to S3 later. Implemented comprehensive image processing with **thumbnail**, **gallery**, and **full-size** versions. Videos are stored as-is without processing.

## Architecture Changes

### 1. Simplified Storage Backend
- **Removed**: Local filesystem and AWS S3 backends
- **Kept**: MinIO backend only (S3-compatible)
- **Benefits**: Consistent API, easier development, cloud-ready architecture

### 2. Enhanced Image Processing
For photo uploads, the system now generates:
- **Thumbnail**: 150x150px for quick previews and lists
- **Gallery**: 800x600px max (maintains aspect ratio) for gallery display
- **Full**: Original resolution for detailed viewing

### 3. Video Storage
- Videos stored as uploaded (no processing for now)
- Can easily add video processing later (thumbnails, compression, etc.)

## Updated Models

### KeepMedia Model Changes
```python
class KeepMedia(models.Model):
    # Storage keys for different sizes
    storage_key_original = models.CharField(max_length=500)  # Original file
    storage_key_thumbnail = models.CharField(max_length=500, blank=True)  # 150x150
    storage_key_gallery = models.CharField(max_length=500, blank=True)    # 800x600
    
    # Image dimensions
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Removed: storage_backend, thumbnail_*_key fields
```

### URL Access Methods
```python
# Get specific size
media.get_url('thumbnail')  # 150x150 version
media.get_url('gallery')    # 800x600 version  
media.get_url('original')   # Full resolution

# Get all available URLs
media.get_all_urls()
# Returns: {
#   'original': 'https://...',
#   'thumbnail': 'https://...',
#   'gallery': 'https://...'
# }
```

## Image Processing Pipeline

### 1. Upload Flow
```
User Upload → Temporary File → Validation → Original Storage → Image Processing
```

### 2. Image Processing Task
```python
@shared_task
def generate_image_sizes(media_id):
    # Load original image
    image = Image.open(BytesIO(image_data))
    
    # Fix EXIF orientation
    image = ImageOps.exif_transpose(image)
    
    # Store dimensions
    media.width, media.height = image.size
    
    # Generate thumbnail (150x150)
    thumbnail = image.copy()
    thumbnail.thumbnail((150, 150), Image.Resampling.LANCZOS)
    
    # Generate gallery (800x600 max, maintain aspect ratio)
    gallery = image.copy()
    gallery.thumbnail((800, 600), Image.Resampling.LANCZOS)
    
    # Save both to MinIO
```

### 3. Quality Settings
- **Thumbnail**: JPEG, 85% quality, optimized
- **Gallery**: JPEG, 90% quality, optimized
- **Original**: Preserved as uploaded

## Configuration Simplified

### Settings Changes
```python
# Removed multiple backend selection
MEDIA_STORAGE_BACKEND = 'minio'

# Only MinIO configuration needed
MINIO_ENDPOINT = 'http://minio:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'
MINIO_BUCKET_NAME = 'tinybeans-media'

# Image processing settings
IMAGE_SIZES = {
    'thumbnail': (150, 150),
    'gallery': (800, 600),
    'full': None,  # Original size
}
```

### Docker Setup (MinIO Only)
```yaml
services:
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
      sleep 10;
      /usr/bin/mc alias set myminio http://minio:9000 minioadmin minioadmin;
      /usr/bin/mc mb myminio/tinybeans-media || true;
      /usr/bin/mc policy set public myminio/tinybeans-media || true;
      "
```

## API Response Changes

### Upload Status Response
```json
{
  "id": "uuid",
  "status": "completed",
  "progress_percentage": 100,
  "media_urls": {
    "original": "https://minio:9000/tinybeans-media/...",
    "thumbnail": "https://minio:9000/tinybeans-media/..._thumb.jpg",
    "gallery": "https://minio:9000/tinybeans-media/..._gallery.jpg"
  }
}
```

### Media Detail Response
```json
{
  "id": 123,
  "media_type": "photo",
  "width": 4032,
  "height": 3024,
  "thumbnails_generated": true,
  "urls": {
    "original": "https://...",
    "thumbnail": "https://...",
    "gallery": "https://..."
  }
}
```

## Benefits of Simplification

### 1. Development Experience
- **Single storage system** to configure and debug
- **Consistent behavior** across all environments
- **S3-compatible** but runs locally
- **Web console** at http://localhost:9001 for file management

### 2. Image Handling
- **Responsive images** - serve appropriate size for context
- **Fast loading** - thumbnails for lists, gallery for viewing
- **High quality** - original always available
- **Efficient storage** - compressed versions reduce bandwidth

### 3. Future-Proof Architecture
- **Easy S3 migration** - MinIO is S3-compatible
- **Scalable processing** - Celery handles image generation
- **Extensible** - can add video processing, AI analysis, etc.

## Usage Examples

### Frontend Image Display
```javascript
// List view - use thumbnails for fast loading
<img src={media.urls.thumbnail} alt={media.caption} />

// Gallery view - use gallery size for good quality
<img src={media.urls.gallery} alt={media.caption} />

// Full screen - use original for maximum quality
<img src={media.urls.original} alt={media.caption} />
```

### Progressive Loading
```javascript
// Load thumbnail first, then gallery
const img = new Image();
img.onload = () => {
  // Show gallery version
  setImageSrc(media.urls.gallery);
};
img.src = media.urls.gallery;

// Show thumbnail immediately
setImageSrc(media.urls.thumbnail);
```

## File Storage Structure

### MinIO Bucket Organization
```
tinybeans-media/
├── keeps/
│   ├── 2024/01/15/
│   │   ├── abc123def456.jpg          # Original
│   │   ├── abc123def456_thumb.jpg    # 150x150
│   │   ├── abc123def456_gallery.jpg  # 800x600
│   │   └── xyz789uvw012.mp4          # Video (no processing)
│   └── 2024/01/16/
│       └── ...
```

### Storage Key Format
- **Original**: `keeps/YYYY/MM/DD/{hash}.{ext}`
- **Thumbnail**: `keeps/YYYY/MM/DD/{hash}_thumb.jpg`
- **Gallery**: `keeps/YYYY/MM/DD/{hash}_gallery.jpg`

## Performance Considerations

### 1. Image Processing
- **Async processing** doesn't block uploads
- **Retry logic** handles temporary failures
- **Quality optimization** balances size vs quality

### 2. URL Generation
- **Presigned URLs** for secure access
- **Configurable expiration** (default 1 hour)
- **Lazy loading** support with multiple sizes

### 3. Storage Efficiency
- **Deduplication** via content hashing
- **Appropriate compression** for each size
- **Format optimization** (always JPEG for processed images)

## Migration Strategy to S3

When ready to move to AWS S3:

### 1. Code Changes (Minimal)
```python
# Just update storage backend
class S3StorageBackend(MinIOStorageBackend):
    # Inherit most functionality
    # Only change endpoint and credentials
    pass
```

### 2. Data Migration
```python
# Copy files from MinIO to S3
def migrate_to_s3():
    minio_backend = MinIOStorageBackend()
    s3_backend = S3StorageBackend()
    
    for media in KeepMedia.objects.all():
        # Copy all versions
        for field in ['storage_key_original', 'storage_key_thumbnail', 'storage_key_gallery']:
            key = getattr(media, field)
            if key:
                content = minio_backend.get_file_content(key)
                s3_backend.save(content, key)
```

### 3. Configuration Update
```python
# Switch to S3 backend
MEDIA_STORAGE_BACKEND = 's3'
AWS_STORAGE_BUCKET_NAME = 'tinybeans-production'
# ... other S3 settings
```

## Next Steps

### Immediate
1. **Test image upload** and verify all sizes are generated
2. **Check MinIO console** to see stored files
3. **Verify URL generation** and access

### Short Term
1. **Add video thumbnails** (extract frame from video)
2. **Implement image optimization** (WebP format support)
3. **Add content analysis** (auto-tagging, inappropriate content detection)

### Long Term
1. **Migrate to AWS S3** when ready for production
2. **Add CDN** for global content delivery
3. **Implement advanced features** (AI-powered auto-tagging, facial recognition)

The simplified MinIO-based architecture provides a solid foundation for TinyBeans' media handling while maintaining flexibility for future enhancements and cloud migration!