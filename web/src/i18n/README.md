# i18n Module

This module implements **ADR-012: Notification Strategy** for standardized backend messages with frontend presentation control.

## Overview

The notification strategy separates concerns:
- **Backend**: Sends i18n keys and context (no translated text)
- **Frontend**: Translates and decides how/when to display messages

## Quick Start

### 1. Using the hook (Recommended)

```typescript
import { useApiMessages } from '@/i18n';

function MyComponent() {
  const { showAsToast, handleError } = useApiMessages();
  
  const onSubmit = async (data) => {
    try {
      const response = await apiClient.post('/endpoint/', data);
      // Optionally show success toast
      showAsToast(response.messages, 200);
    } catch (error) {
      // Show error toast and get field errors
      const fieldErrors = handleError(error);
      // Use fieldErrors for inline form validation
    }
  };
}
```

### 2. Manual translation

```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  // Translate a message
  const message = t('errors.file_too_large', { 
    filename: 'photo.jpg', 
    maxSize: '10MB' 
  });
}
```

### 3. Change language

```typescript
import { useTranslation } from 'react-i18next';

function LanguageSwitcher() {
  const { i18n } = useTranslation();
  
  const changeLanguage = async (lang: 'en' | 'es') => {
    await i18n.changeLanguage(lang);
    // Update user preference on backend
    await apiClient.patch('/profile/', { language: lang });
  };
}
```

## API Response Format

### Success Response (Optional Messages)
```json
{
  "data": { "id": 123 },
  "messages": [
    {
      "i18n_key": "notifications.profile.updated",
      "context": {}
    }
  ]
}
```

### Error Response (Required Messages)
```json
{
  "error": "validation_failed",
  "messages": [
    {
      "i18n_key": "errors.email_invalid",
      "context": { "field": "email" }
    }
  ]
}
```

## Translation Files

Add translations to:
- `src/i18n/locales/en.json` - English
- `src/i18n/locales/es.json` - Spanish

### Example Entry
```json
{
  "errors": {
    "file_too_large": "File {{filename}} is too large. Maximum size is {{maxSize}}."
  }
}
```

## Utilities

### `useApiMessages()` Hook

- `translate(messages)` - Translate message array
- `translateOne(message)` - Translate single message
- `showAsToast(messages, status)` - Show as toast notification
- `getFieldErrors(messages)` - Extract field-level errors
- `getGeneral(messages)` - Get non-field errors
- `handleError(error)` - Show general errors as toast, return field errors
- `handleSuccess(response)` - Optionally show success toast

### Direct Functions

- `translateMessages(messages, t)` - Translate array
- `translateMessage(message, t)` - Translate one
- `extractFieldErrors(messages, t)` - Get field errors map
- `getGeneralErrors(messages, t)` - Get general errors
- `inferSeverity(status)` - Get severity from HTTP status

## Examples

See `EXAMPLES.tsx` for complete usage patterns:
1. Inline feedback (suppress messages)
2. Toast notifications
3. Form validation with field errors
4. Multiple messages
5. Custom translation
6. Language switching

## Backend Implementation

See `mysite/mysite/notification_utils.py` for backend utilities:

```python
from mysite.notification_utils import create_message, error_response

# Single error
error_response(
    'file_too_large',
    [create_message('errors.file_too_large', {
        'filename': 'photo.jpg',
        'maxSize': '10MB'
    })],
    status.HTTP_400_BAD_REQUEST
)

# Multiple validation errors
validation_error_response([
    create_message('errors.email_invalid', {'field': 'email'}),
    create_message('errors.password_too_short', {'field': 'password', 'minLength': 8})
])
```

## Migration Guide

### Old Code (Auto-toast)
```typescript
// ❌ Messages shown automatically
const response = await api.post('/endpoint/', data);
```

### New Code (Explicit control)
```typescript
// ✅ Component decides when/how to show messages
const { handleError } = useApiMessages();
try {
  const response = await apiClient.post('/endpoint/', data);
  // Show inline feedback or navigate
} catch (error) {
  const fieldErrors = handleError(error);
  // Use fieldErrors in form
}
```

## Benefits

- ✅ No duplicate messages
- ✅ Context-aware display (toast vs inline)
- ✅ Instant language switching
- ✅ Clean separation of concerns
- ✅ User language preference stored in profile

## Related Files

- `config.ts` - i18n initialization
- `notificationUtils.ts` - Message handling utilities
- `useApiMessages.ts` - React hook for API messages
- `EXAMPLES.tsx` - Usage examples
- `locales/` - Translation files
