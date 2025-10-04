# Backend Notification Utilities

This module implements **ADR-012: Notification Strategy** for Django REST Framework views.

## Overview

API responses return i18n keys with context, allowing the frontend to translate and display messages appropriately.

## Quick Start

### Import

```python
from mysite.notification_utils import (
    create_message,
    success_response,
    error_response,
    validation_error_response,
    rate_limit_response
)
```

### Simple Error

```python
def my_view(request):
    if file_size > MAX_SIZE:
        return error_response(
            'file_too_large',
            [create_message('errors.file_too_large', {
                'filename': file.name,
                'maxSize': '10MB'
            })],
            status.HTTP_400_BAD_REQUEST
        )
```

### Validation Errors

```python
def update_profile(request):
    errors = []
    
    if not is_valid_email(request.data.get('email')):
        errors.append(create_message('errors.email_invalid', {'field': 'email'}))
    
    if len(request.data.get('password', '')) < 8:
        errors.append(create_message('errors.password_too_short', {
            'field': 'password',
            'minLength': 8
        }))
    
    if errors:
        return validation_error_response(errors)
    
    # Process valid data...
```

### Success Response

```python
def create_item(request):
    item = Item.objects.create(**request.data)
    
    # Success responses rarely need messages
    # Frontend handles with optimistic UI
    return success_response(
        {'id': item.id, 'name': item.name},
        status_code=status.HTTP_201_CREATED
    )
```

### Success with Message

```python
def sync_data(request):
    # Background operation completed
    result = perform_sync()
    
    return success_response(
        {'synced_count': result.count},
        messages=[create_message('notifications.sync.completed', {
            'count': result.count
        })]
    )
```

## API Reference

### `create_message(i18n_key, context=None)`

Create a standardized message object.

**Parameters:**
- `i18n_key` (str): Translation key from frontend i18n files
- `context` (dict, optional): Flat dictionary with dynamic values

**Returns:** Dictionary with `i18n_key` and optional `context`

**Example:**
```python
msg = create_message('errors.file_too_large', {
    'filename': 'photo.jpg',
    'maxSize': '10MB'
})
# {'i18n_key': 'errors.file_too_large', 'context': {'filename': 'photo.jpg', 'maxSize': '10MB'}}
```

### `success_response(data, messages=None, status_code=200)`

Create a success response.

**Parameters:**
- `data` (dict): Response data
- `messages` (list, optional): List of message objects
- `status_code` (int): HTTP status code (default: 200)

**Returns:** DRF Response object

**Example:**
```python
return success_response(
    {'user_id': user.id},
    messages=[create_message('notifications.profile.updated')],
    status_code=status.HTTP_200_OK
)
```

### `error_response(error, messages, status_code=400)`

Create an error response.

**Parameters:**
- `error` (str): Machine-readable error code
- `messages` (list): List of message objects (required)
- `status_code` (int): HTTP status code (default: 400)

**Returns:** DRF Response object

**Example:**
```python
return error_response(
    'file_too_large',
    [create_message('errors.file_too_large', {'filename': name, 'maxSize': '10MB'})],
    status.HTTP_400_BAD_REQUEST
)
```

### `validation_error_response(messages, status_code=400)`

Create a validation error response (convenience function).

**Parameters:**
- `messages` (list): List of message objects with field context
- `status_code` (int): HTTP status code (default: 400)

**Returns:** DRF Response object

**Example:**
```python
return validation_error_response([
    create_message('errors.email_invalid', {'field': 'email'}),
    create_message('errors.password_too_short', {'field': 'password', 'minLength': 8})
])
```

### `rate_limit_response(i18n_key='errors.rate_limit', context=None)`

Create a rate limit response (429 status).

**Parameters:**
- `i18n_key` (str): Translation key for rate limit message
- `context` (dict, optional): Optional context (e.g., retry_after)

**Returns:** DRF Response object

**Example:**
```python
return rate_limit_response('errors.rate_limit', {'retry_after': 60})
```

## Response Formats

### Success Response (No Messages)
```json
{
  "data": {
    "id": 123,
    "name": "Item Name"
  }
}
```

### Success Response (With Messages)
```json
{
  "data": {
    "synced_count": 42
  },
  "messages": [
    {
      "i18n_key": "notifications.sync.completed",
      "context": {
        "count": 42
      }
    }
  ]
}
```

### Error Response
```json
{
  "error": "file_too_large",
  "messages": [
    {
      "i18n_key": "errors.file_too_large",
      "context": {
        "filename": "vacation-photo.jpg",
        "maxSize": "10MB"
      }
    }
  ]
}
```

### Validation Errors
```json
{
  "error": "validation_failed",
  "messages": [
    {
      "i18n_key": "errors.email_invalid",
      "context": {
        "field": "email"
      }
    },
    {
      "i18n_key": "errors.password_too_short",
      "context": {
        "field": "password",
        "minLength": 8
      }
    }
  ]
}
```

## Best Practices

### ✅ Do
- Keep context flat (no nested objects)
- Use semantic error codes (`file_too_large`, `validation_failed`)
- Only include messages when needed (typically errors)
- Rely on HTTP status for severity (2xx=success, 4xx=client error, 5xx=server error)
- Add all i18n keys to frontend translation files

### ❌ Don't
- Don't include translated text in backend responses
- Don't specify severity level (use HTTP status)
- Don't specify presentation channel (toast/inline/modal)
- Don't nest objects in context
- Don't send messages for simple success responses (frontend handles with optimistic UI)

## Migration from Old Code

### Old Code
```python
# ❌ Old response format
return Response(
    {'error': 'File is too large. Maximum size is 10MB.'},
    status=status.HTTP_400_BAD_REQUEST
)
```

### New Code
```python
# ✅ New format with i18n key
from mysite.notification_utils import error_response, create_message

return error_response(
    'file_too_large',
    [create_message('errors.file_too_large', {
        'filename': file.name,
        'maxSize': '10MB'
    })],
    status.HTTP_400_BAD_REQUEST
)
```

## Adding Translation Keys

When adding new i18n keys:

1. **Choose a descriptive key:**
   ```python
   'errors.file_too_large'  # Good
   'error1'  # Bad
   ```

2. **Add to frontend translation files:**
   - `web/src/i18n/locales/en.json`
   - `web/src/i18n/locales/es.json`

3. **Use consistent context parameters:**
   ```python
   {'filename': '...', 'maxSize': '...'}  # Good
   {'file': '...', 'max': '...'}  # Less clear
   ```

## Testing

Test responses include correct structure:

```python
def test_error_response_format(self):
    response = self.client.post('/api/upload/', {'file': large_file})
    
    self.assertEqual(response.status_code, 400)
    self.assertIn('error', response.data)
    self.assertIn('messages', response.data)
    
    messages = response.data['messages']
    self.assertEqual(len(messages), 1)
    self.assertEqual(messages[0]['i18n_key'], 'errors.file_too_large')
    self.assertIn('filename', messages[0]['context'])
```

## Related Files

- `mysite/notification_utils.py` - This module
- `web/src/i18n/` - Frontend i18n implementation
- `docs/architecture/adr/ADR-012-NOTIFICATION-STRATEGY.md` - Full ADR documentation
