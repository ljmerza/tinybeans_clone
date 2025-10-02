# Keeps App API Schema Documentation

## Overview

The Keeps app provides RESTful APIs for managing family memories (keeps) within family circles. This document outlines the complete API schema for all endpoints.

## Base URL

All endpoints are prefixed with `/api/keeps/`

## Authentication

All endpoints require authentication via JWT tokens passed in cookies or Authorization header.

## Permissions

- **Circle Member**: User must be a member of the circle containing the keep/resource
- **Circle Admin or Owner**: User must be either a circle admin or the creator/owner of the resource

## Keep Endpoints

### List/Create Keeps

**Endpoint**: `GET/POST /api/keeps/`

**Permissions**: Circle Member

#### GET - List Keeps
Lists keeps from all circles the authenticated user belongs to.

**Query Parameters**:
- `keep_type`: Filter by type (`note`, `media`, `milestone`)
- `circle`: Filter by circle ID (UUID)
- `circle_slug`: Filter by circle slug
- `tag`: Filter by tag (partial match)
- `search`: Full-text search in title, description, and tags
- `ordering`: Order by field (`date_of_memory`, `-date_of_memory`, `created_at`, `-created_at`)

**Response**: Paginated list of keeps
```json
{
  "count": 25,
  "next": "http://example.com/api/keeps/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "circle": "uuid",
      "circle_name": "Smith Family",
      "created_by": 1,
      "created_by_username": "john_smith",
      "keep_type": "media",
      "title": "First Steps",
      "description": "Baby's first steps in the garden",
      "date_of_memory": "2023-12-01",
      "created_at": "2023-12-01T10:30:00Z",
      "updated_at": "2023-12-01T10:30:00Z",
      "is_public": false,
      "tags": "baby,milestone,walking",
      "tag_list": ["baby", "milestone", "walking"],
      "media_count": 2,
      "reaction_count": 5,
      "comment_count": 3
    }
  ]
}
```

#### POST - Create Keep
Creates a new family memory.

**Request Body**:
```json
{
  "circle": "uuid",
  "keep_type": "media",
  "title": "First Steps",
  "description": "Baby's first steps in the garden",
  "date_of_memory": "2023-12-01",
  "is_public": false,
  "tags": "baby,milestone,walking",
  "media_files": [
    {
      "media_type": "photo",
      "caption": "Taking first steps",
      "upload_order": 1
    }
  ],
  "milestone_data": {
    "milestone_type": "first_steps",
    "child_profile": "uuid",
    "age_at_milestone": "365",
    "notes": "Walked from couch to table",
    "is_first_time": true
  }
}
```

**Response**: Created keep object (201)

### Retrieve/Update/Delete Keep

**Endpoint**: `GET/PUT/PATCH/DELETE /api/keeps/{keep_id}/`

**Permissions**: 
- GET: Circle Member
- PUT/PATCH/DELETE: Circle Admin or Owner

#### GET - Retrieve Keep
Returns detailed keep information including all related data.

**Response**:
```json
{
  "id": "uuid",
  "circle": "uuid",
  "circle_name": "Smith Family",
  "created_by": 1,
  "created_by_username": "john_smith",
  "keep_type": "media",
  "title": "First Steps",
  "description": "Baby's first steps in the garden",
  "date_of_memory": "2023-12-01",
  "created_at": "2023-12-01T10:30:00Z",
  "updated_at": "2023-12-01T10:30:00Z",
  "is_public": false,
  "tags": "baby,milestone,walking",
  "tag_list": ["baby", "milestone", "walking"],
  "media_count": 2,
  "reaction_count": 5,
  "comment_count": 3,
  "media_files": [
    {
      "id": 1,
      "media_type": "photo",
      "caption": "Taking first steps",
      "upload_order": 1,
      "file_size": 2048000,
      "original_filename": "first_steps.jpg",
      "content_type": "image/jpeg",
      "width": 1920,
      "height": 1080,
      "thumbnails_generated": true,
      "urls": {
        "original": "https://storage.example.com/original/...",
        "thumbnail": "https://storage.example.com/thumb/...",
        "gallery": "https://storage.example.com/gallery/..."
      },
      "created_at": "2023-12-01T10:30:00Z"
    }
  ],
  "milestone": {
    "milestone_type": "first_steps",
    "child_profile": "uuid",
    "child_name": "Emma Smith",
    "age_at_milestone": "365",
    "notes": "Walked from couch to table",
    "is_first_time": true
  },
  "reactions": [
    {
      "id": 1,
      "user": 2,
      "user_username": "mary_smith",
      "reaction_type": "love",
      "created_at": "2023-12-01T11:00:00Z"
    }
  ],
  "comments": [
    {
      "id": 1,
      "user": 2,
      "user_username": "mary_smith",
      "comment": "So proud of our little walker!",
      "created_at": "2023-12-01T11:15:00Z",
      "updated_at": "2023-12-01T11:15:00Z"
    }
  ]
}
```

#### PUT/PATCH - Update Keep
Updates keep information. Only title, description, date_of_memory, is_public, and tags can be modified.

**Request Body** (PATCH example):
```json
{
  "title": "Emma's First Steps",
  "tags": "baby,milestone,walking,emma"
}
```

#### DELETE - Delete Keep
Permanently deletes the keep and all associated media, reactions, and comments.

**Response**: 204 No Content

## Media Upload Endpoints

### Upload Media File

**Endpoint**: `POST /api/keeps/upload/`

**Permissions**: Circle Member

**Content-Type**: `multipart/form-data`

**Request**:
```
keep_id: uuid
media_type: photo | video
file: [binary file data]
caption: string (optional)
upload_order: integer (optional, default: 0)
```

**Response**: Upload initiated (202)
```json
{
  "id": "upload-uuid",
  "keep": "keep-uuid",
  "keep_title": "First Steps",
  "media_type": "photo",
  "original_filename": "IMG_001.jpg",
  "content_type": "image/jpeg",
  "file_size": 2048000,
  "caption": "Taking first steps",
  "upload_order": 1,
  "status": "pending",
  "error_message": "",
  "created_at": "2023-12-01T10:30:00Z",
  "updated_at": "2023-12-01T10:30:00Z"
}
```

### Check Upload Status

**Endpoint**: `GET /api/keeps/upload/{upload_id}/status/`

**Permissions**: Circle Member

**Response**:
```json
{
  "id": "upload-uuid",
  "keep": "keep-uuid",
  "keep_title": "First Steps",
  "media_type": "photo",
  "original_filename": "IMG_001.jpg",
  "status": "completed",
  "error_message": "",
  "progress_percentage": 100,
  "media_urls": {
    "original": "https://storage.example.com/original/...",
    "thumbnail": "https://storage.example.com/thumb/...",
    "gallery": "https://storage.example.com/gallery/..."
  },
  "created_at": "2023-12-01T10:30:00Z",
  "updated_at": "2023-12-01T10:32:00Z"
}
```

**Status Values**:
- `pending`: Upload received, waiting for validation
- `validating`: File being validated
- `processing`: Creating thumbnails/processing
- `completed`: Ready for use
- `failed`: Processing failed (see error_message)

## Reaction Endpoints

### List/Create Reactions

**Endpoint**: `GET/POST /api/keeps/reactions/`

**Permissions**: Circle Member

#### GET - List Reactions
Lists all reactions to keeps in user's circles.

#### POST - Create Reaction
Adds a reaction to a keep. Each user can only have one reaction per keep.

**Request Body**:
```json
{
  "keep": "keep-uuid",
  "reaction_type": "love"
}
```

**Reaction Types**: `like`, `love`, `laugh`, `wow`, `celebrate`

### Retrieve/Update/Delete Reaction

**Endpoint**: `GET/PUT/PATCH/DELETE /api/keeps/reactions/{reaction_id}/`

**Permissions**:
- GET: Circle Member
- PUT/PATCH/DELETE: Circle Admin or Owner

## Comment Endpoints

### List/Create Comments

**Endpoint**: `GET/POST /api/keeps/comments/`

**Permissions**: Circle Member

#### POST - Create Comment
Adds a comment to a keep.

**Request Body**:
```json
{
  "keep": "keep-uuid",
  "comment": "So proud of our little walker!"
}
```

### Retrieve/Update/Delete Comment

**Endpoint**: `GET/PUT/PATCH/DELETE /api/keeps/comments/{comment_id}/`

**Permissions**:
- GET: Circle Member
- PUT/PATCH/DELETE: Circle Admin or Owner

## Media Endpoints

### List/Create Media

**Endpoint**: `GET/POST /api/keeps/media/`

**Permissions**: Circle Member

Note: For creating media, use the upload endpoints instead.

### Retrieve/Delete Media

**Endpoint**: `GET/DELETE /api/keeps/media/{media_id}/`

**Permissions**:
- GET: Circle Member
- DELETE: Circle Admin or Owner

## Utility Endpoints

### Get Keeps by Circle

**Endpoint**: `GET /api/keeps/by-circle/{circle_slug}/`

**Permissions**: Circle Member

Returns all keeps for a specific circle.

### Get Keeps by Type

**Endpoint**: `GET /api/keeps/by-type/?type={type}`

**Permissions**: Circle Member

**Query Parameters**:
- `type`: Required. One of `note`, `media`, `milestone`

Returns keeps of the specified type from all user's circles.

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Descriptive error message",
  "details": {
    "field_name": ["Field-specific error messages"]
  }
}
```

**Common HTTP Status Codes**:
- `400`: Bad Request - Invalid data or parameters
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Permission denied
- `404`: Not Found - Resource not found
- `413`: Payload Too Large - File too large
- `500`: Internal Server Error - Server error

## File Upload Limits

- **Maximum file size**: 100MB (configurable)
- **Supported image types**: JPEG, PNG, GIF, WebP
- **Supported video types**: MP4, MOV, AVI, WebM

## Media Processing

When photos are uploaded:
1. Original file is stored
2. Thumbnail version (150x150) is generated
3. Gallery version (800x600) is generated
4. All versions are stored in MinIO/S3

Videos are stored as-is without processing (for now).

## Rate Limiting

Upload endpoints are rate-limited to prevent abuse:
- 50 uploads per hour per user
- 10GB total uploads per day per user

## Pagination

List endpoints use cursor-based pagination:
- Default page size: 20
- Maximum page size: 100
- Use `page` parameter for navigation

## Caching

- Media URLs are cached for 1 hour
- Keep metadata is cached for 5 minutes
- Circle membership is cached for 30 minutes