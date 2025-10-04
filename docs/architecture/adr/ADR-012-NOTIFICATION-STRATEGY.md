# ADR-012: API Message Handling Strategy

## Status
**Accepted** - *Date: 2024-06-06*  
**Owner:** Web Platform Team

## Context

Users currently receive duplicate notifications because the API returns raw message strings that are automatically shown as toasts, while the frontend also shows its own inline feedback. This creates a poor UX with duplicated messages and makes it unclear who controls message presentation.

## Decision

All API endpoints will return messages in a standardized format, and the frontend will have full control over when and how to present them.

### Backend Implementation

All API responses include a `messages` array:

```json
{
  "data": { /* response data */ },
  "messages": [
    {
      "i18n_key": "notifications.profile.photo_uploaded",
      "default_message": "Profile photo updated successfully",
      "context": {}
    }
  ]
}
```

**Message structure:**
- `i18n_key`: Translation key from frontend i18n files (e.g., `notifications.profile.photo_uploaded`)
- `default_message`: English fallback for development/logging
- `context`: Optional object with dynamic values for parameterized messages (e.g., `{ filename: "photo.jpg", maxSize: "10MB" }`)

**Backend does NOT specify:**
- Severity level (conveyed by HTTP status: `2xx` = success, `4xx` = client error, `5xx` = server error)
- Presentation channel (toast/inline/modal - this is a frontend decision)

### Frontend Implementation

**1. HTTP Status determines severity:**
- `2xx` → success
- `4xx` → warning/error
- `5xx` → error

**2. Internationalization with react-i18next:**

Install the i18n library:
```bash
npm install react-i18next i18next
```

**Setup configuration:**
```typescript
// src/i18n/config.ts
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import es from './locales/es.json';

i18next
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      es: { translation: es }
    },
    lng: 'en', // default language
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false // React already escapes
    }
  });

export default i18next;
```

**Translation files structure:**
```json
// src/i18n/locales/en.json
{
  "notifications": {
    "profile": {
      "photo_uploaded": "Profile photo updated successfully"
    }
  },
  "errors": {
    "file_too_large": "File {{filename}} is too large. Maximum size is {{maxSize}}."
  }
}

// src/i18n/locales/es.json
{
  "notifications": {
    "profile": {
      "photo_uploaded": "Foto de perfil actualizada exitosamente"
    }
  },
  "errors": {
    "file_too_large": "El archivo {{filename}} es demasiado grande. El tamaño máximo es {{maxSize}}."
  }
}
```

**Usage in components:**
```typescript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  // Simple translation
  const message = t('notifications.profile.photo_uploaded');
  
  // With interpolation (context)
  const errorMsg = t('errors.file_too_large', {
    filename: 'photo.jpg',
    maxSize: '10MB'
  });
  
  return <div>{message}</div>;
}
```

**3. Components explicitly control message display:**
```typescript
import { useTranslation } from 'react-i18next';

// Component with inline feedback - suppress API messages
const { mutate } = useUploadPhoto({
  onSuccess: (response) => {
    // Already showing inline UI feedback
    // Don't display response.messages
  }
});

// Background operation - show as toast
const { mutate } = useSyncData({
  onSuccess: (response) => {
    const { t } = useTranslation();
    response.messages.forEach(msg => {
      showToast({
        message: t(msg.i18n_key, msg.context),
        type: 'success' // inferred from 200 status
      });
    });
  }
});
```

**4. Remove automatic global toast behavior:**
- Shared HTTP client should NOT auto-toast messages
- Each component/hook decides if/how to show messages
- This prevents duplicate messages and gives context-aware control

### Examples

**Simple success message:**
```json
HTTP/1.1 200 OK

{
  "data": { "photoUrl": "https://..." },
  "messages": [
    {
      "i18n_key": "notifications.profile.photo_uploaded",
      "default_message": "Profile photo updated successfully",
      "context": {}
    }
  ]
}
```

**Parameterized error message:**
```json
HTTP/1.1 400 Bad Request

{
  "error": "file_too_large",
  "messages": [
    {
      "i18n_key": "errors.file_too_large",
      "default_message": "File {{filename}} is too large. Maximum size is {{maxSize}}.",
      "context": {
        "filename": "vacation-photo.jpg",
        "maxSize": "10MB"
      }
    }
  ]
}
```

**Frontend handles translation:**
```typescript
const { t } = useTranslation();

// Backend sends: i18n_key="errors.file_too_large", context={filename: "vacation-photo.jpg", maxSize: "10MB"}
const message = t('errors.file_too_large', { filename: 'vacation-photo.jpg', maxSize: '10MB' });

// English user sees: "File vacation-photo.jpg is too large. Maximum size is 10MB."
// Spanish user sees: "El archivo vacation-photo.jpg es demasiado grande. El tamaño máximo es 10MB."
```

## Implementation Tasks

### Backend
1. Update all API endpoints to return `messages` array with `i18n_key`, `default_message`, and `context`
2. Remove `level` and `channel` fields - rely on HTTP status for severity
3. Document message schema in OpenAPI specs

### Frontend
1. Install react-i18next: `npm install react-i18next i18next`
2. Create i18n configuration file with language resources
3. Create translation files structure under `src/i18n/locales/`
4. Add all message i18n keys to translation files for each supported language
5. Create utility functions for message handling:
   - Infer severity from HTTP status
   - Provide presenters for different channels (toast, inline, modal)
6. Update shared HTTP client to remove automatic toast behavior
7. Update all components/hooks to explicitly handle messages using `useTranslation()`:
   - Decide whether to show messages based on UI context
   - Translate messages with `t(msg.i18n_key, msg.context)`
   - Choose appropriate presentation channel
   - Suppress messages when optimistic UI provides feedback
8. Add tests ensuring all i18n keys exist in translation files

## Benefits

- **No duplicate messages:** Frontend controls when to display
- **Context-aware:** Same message shown differently based on UI state
- **Internationalization:** Client-side translation with instant language switching
- **Clean separation:** Backend = domain events, Frontend = presentation
- **HTTP semantics:** Uses status codes instead of duplicating severity
- **Standard library:** react-i18next is the most popular i18n solution for React apps
