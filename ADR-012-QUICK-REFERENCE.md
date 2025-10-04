# ADR-012 Quick Reference Guide

## For Backend Developers

### Basic Error Response

```python
from mysite.notification_utils import error_response, create_message
from rest_framework import status

# Single error
if file.size > MAX_SIZE:
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
from mysite.notification_utils import validation_error_response, create_message

errors = []
if not valid_email(data['email']):
    errors.append(create_message('errors.email_invalid', {'field': 'email'}))

if len(data['password']) < 8:
    errors.append(create_message('errors.password_too_short', {
        'field': 'password',
        'minLength': 8
    }))

if errors:
    return validation_error_response(errors)
```

### Success Response

```python
from mysite.notification_utils import success_response

# Usually no message needed
return success_response({'id': item.id})

# With optional message for background operations
return success_response(
    {'count': synced},
    messages=[create_message('notifications.sync.completed', {'count': synced})]
)
```

## For Frontend Developers

### Basic Usage

```typescript
import { useApiMessages } from '@/i18n';
import { apiClient } from '@/features/auth/api/modernAuthClient';

function MyComponent() {
  const { handleError } = useApiMessages();
  
  const onSubmit = async (data) => {
    try {
      await apiClient.post('/endpoint/', data);
      // Show success feedback
    } catch (error) {
      const fieldErrors = handleError(error);
      // Use fieldErrors in form
    }
  };
}
```

### Show Toast

```typescript
const { showAsToast } = useApiMessages();

try {
  const response = await apiClient.post('/sync/', {});
  showAsToast(response.messages, 200);
} catch (error) {
  showAsToast(error.messages, error.status || 400);
}
```

### Form Validation

```typescript
const { getFieldErrors, getGeneral } = useApiMessages();

try {
  await apiClient.patch('/profile/', data);
} catch (error) {
  const fieldErrors = getFieldErrors(error.messages);
  const generalErrors = getGeneral(error.messages);
  
  // Set field errors: fieldErrors = { email: "Invalid email", ... }
  // Show general errors in toast or at top of form
}
```

### Change Language

```typescript
import { useTranslation } from 'react-i18next';

const { i18n } = useTranslation();

const changeLanguage = async (lang: 'en' | 'es') => {
  await i18n.changeLanguage(lang);
  await apiClient.patch('/profile/', { language: lang });
};
```

## Adding New Messages

### 1. Choose i18n Key

Use descriptive, hierarchical keys:
- `errors.file_too_large` ✅
- `errors.validation_failed` ✅
- `error1` ❌

### 2. Add to Translation Files

**web/src/i18n/locales/en.json:**
```json
{
  "errors": {
    "my_new_error": "Description with {{param}}"
  }
}
```

**web/src/i18n/locales/es.json:**
```json
{
  "errors": {
    "my_new_error": "Descripción con {{param}}"
  }
}
```

### 3. Use in Backend

```python
return error_response(
    'my_error_code',
    [create_message('errors.my_new_error', {'param': 'value'})],
    status.HTTP_400_BAD_REQUEST
)
```

## Common Patterns

### Pattern 1: Inline Feedback
Component shows its own UI, suppress API messages.

```typescript
// Backend sends no messages
return success_response({'photo_url': url})

// Frontend shows inline
<img src={photoUrl} /> // Photo updated successfully
```

### Pattern 2: Background Operation
Show toast for async operations user isn't watching.

```typescript
const { showAsToast } = useApiMessages();
const response = await apiClient.post('/sync/', {});
showAsToast(response.messages, 200);
```

### Pattern 3: Form Validation
Show errors next to form fields.

```typescript
const { getFieldErrors, getGeneral } = useApiMessages();

try {
  await apiClient.post('/submit/', data);
} catch (error) {
  const fieldErrors = getFieldErrors(error.messages);
  // { email: "Invalid", password: "Too short" }
  
  // Set each field error in form
  Object.entries(fieldErrors).forEach(([field, msg]) => {
    form.setError(field, msg);
  });
  
  // Show general errors at top
  const general = getGeneral(error.messages);
  if (general.length > 0) {
    setFormError(general.join('\n'));
  }
}
```

## Response Format Reference

### Success (200-299)
```json
{
  "data": { /* your data */ },
  "messages": [ /* optional */ ]
}
```

### Client Error (400-499)
```json
{
  "error": "error_code",
  "messages": [
    {
      "i18n_key": "errors.something",
      "context": { "field": "email" }
    }
  ]
}
```

### Server Error (500-599)
```json
{
  "error": "server_error",
  "messages": [
    {
      "i18n_key": "errors.server_error",
      "context": {}
    }
  ]
}
```

## Key Rules

### Backend
- ✅ Send i18n_key, not translated text
- ✅ Keep context flat (no nesting)
- ✅ Use HTTP status for severity
- ✅ Only include messages when needed
- ❌ Don't specify presentation channel
- ❌ Don't send severity level

### Frontend
- ✅ Component decides when/how to show messages
- ✅ Use `useApiMessages()` hook
- ✅ Translate with `t(i18n_key, context)`
- ✅ Show field errors inline
- ❌ Don't auto-toast everything
- ❌ Don't ignore error messages

## Migration Checklist

### Backend Endpoint
- [ ] Import `notification_utils`
- [ ] Replace `Response()` with `success_response()` or `error_response()`
- [ ] Use `create_message()` for all user-facing text
- [ ] Add i18n keys to frontend translation files
- [ ] Test response format

### Frontend Component
- [ ] Import `useApiMessages`
- [ ] Use `modernAuthClient` instead of `api`
- [ ] Handle messages explicitly (don't rely on auto-toast)
- [ ] Decide: toast, inline, or suppress?
- [ ] Test all error scenarios

## Troubleshooting

**"Missing translation key"**
→ Add key to both en.json and es.json

**"Duplicate messages"**
→ Remove auto-toast callbacks, use explicit handling

**"Context not interpolating"**
→ Check context is flat object, not nested

**"Language not changing"**
→ Ensure user.language field updated on backend

## Documentation

- Full ADR: `docs/architecture/adr/ADR-012-NOTIFICATION-STRATEGY.md`
- Backend Docs: `mysite/mysite/NOTIFICATION_UTILS_README.md`
- Frontend Docs: `web/src/i18n/README.md`
- Examples: `web/src/i18n/EXAMPLES.tsx`
- Implementation Summary: `ADR-012-IMPLEMENTATION-SUMMARY.md`
