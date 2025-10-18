# ADR-012: Notification Strategy (Standardized Backend Messages & Frontend Presentation Control)

## Status
**Accepted** - *Date: 2024-06-06*  
**Owner:** Web Platform Team

## Context

Users currently receive duplicate notifications because the API returns raw message strings that are automatically shown as toasts, while the frontend also shows its own inline feedback. This creates a poor UX with duplicated messages and makes it unclear who 
controls message presentation.

## Decision

All API endpoints will return messages in a standardized format, and the frontend will have full control over when and how to 
present them.

### Backend Implementation

API responses include a `messages` array when there are messages to display (typically for errors):

```json
{
  "data": { /* response data */ },
  "messages": [
    {
      "i18n_key": "notifications.profile.photo_uploaded",
      "context": {}
    }
  ]
}
```

**Message structure:**
- `i18n_key`: Translation key from frontend i18n files (e.g., `notifications.profile.photo_uploaded`)
- `context`: Optional object with dynamic values for parameterized messages (e.g., `{ filename: "photo.jpg", maxSize: "10MB" }`). 
Keep flat - no nested objects.

**Backend does NOT specify:**
- Severity level (conveyed by HTTP status: `2xx` = success, `4xx` = client error, `5xx` = server error)
- Presentation channel (toast/inline/modal - this is a frontend decision)
- Default message text (translation is frontend's responsibility)

**Key rules:**
- `messages` array is optional - only include when needed (typically errors)
- Success responses rarely need messages (frontend handles with optimistic UI)
- Error responses don't need `data` property
- If multiple messages, frontend shows all together
- Keep `context` simple - flat key-value pairs only
- No naming convention enforced on `i18n_key` - backend doesn't dictate frontend structure

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
    fallbackLng: 'en', // missing keys fall back to English
    interpolation: {
      escapeValue: false // React already escapes
    }
  });

export default i18next;
```

**Load user's preferred language:**
```typescript
// When user logs in or profile loads
const userLanguage = user.language; // from user model
i18next.changeLanguage(userLanguage);
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
    
    // If multiple messages, show all together
    if (response.messages?.length > 0) {
      const allMessages = response.messages
        .map(msg => t(msg.i18n_key, msg.context))
        .join('\n');
      
      showToast({
        message: allMessages,
        type: 'success' // inferred from 200 status
      });
    }
  }
});

// Error handling - show in context
const { mutate } = useUpdateProfile({
  onError: (error) => {
    const { t } = useTranslation();
    
    // Show errors inline near the form, not as toast
    error.response.messages?.forEach(msg => {
      const translatedMsg = t(msg.i18n_key, msg.context);
      
      // If context has a field, show next to that field
      if (msg.context?.field) {
        setFieldError(msg.context.field, translatedMsg);
      } else {
        // General error, show at top of form
        setFormError(translatedMsg);
      }
    });
  }
});
```

**4. Remove automatic global toast behavior:**
- Shared HTTP client should NOT auto-toast messages
- Each component/hook decides if/how to show messages
- This prevents duplicate messages and gives context-aware control

### Examples

**Success response (no message needed):**
```json
HTTP/1.1 200 OK

{
  "data": { "photoUrl": "https://..." }
}
```
Frontend handles success feedback with optimistic UI.

**Error response (no data property):**
```json
HTTP/1.1 400 Bad Request

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

**Multiple validation errors:**
```json
HTTP/1.1 400 Bad Request

{
  "error": "validation_failed",
  "messages": [
    {
      "i18n_key": "errors.email_invalid",
      "context": { "field": "email" }
    },
    {
      "i18n_key": "errors.password_too_short",
      "context": { "field": "password", "minLength": 8 }
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
1. Update all API endpoints to optionally return `messages` array with `i18n_key` and `context`
2. Remove `default_message` field - frontend owns all translations
3. Remove `level` and `channel` fields - rely on HTTP status for severity
4. Keep `context` simple - flat key-value pairs only, no nesting
5. Only include `messages` when needed (typically errors)
6. Document message schema in OpenAPI specs
7. **Add `language` field to User model** with choices (e.g., `en`, `es`, `fr`)

### Frontend
1. Install react-i18next: `npm install react-i18next i18next`
2. Create i18n configuration file with language resources
3. Configure fallback to English for missing translation keys
4. Create translation files structure under `src/i18n/locales/`
5. Add all message i18n keys to translation files for each supported language
6. Load user's preferred language on login: `i18next.changeLanguage(user.language)`
7. Create utility functions for message handling:
  - Infer severity from HTTP status
  - Handle multiple messages (show all together)
  - Provide presenters for different channels (toast, inline, modal)
8. Update shared HTTP client to remove automatic toast behavior
9. Update all components/hooks to explicitly handle messages using `useTranslation()`:
  - Decide whether to show messages based on UI context
  - Translate messages with `t(msg.i18n_key, msg.context)`
  - Show multiple messages together if present
  - Choose appropriate presentation channel
  - Route field-level errors to specific form fields using `context.field`
  - Suppress messages when optimistic UI provides feedback
10. Add tests ensuring all i18n keys exist in translation files

## Benefits

- **No duplicate messages:** Frontend controls when to display
- **Context-aware:** Same message shown differently based on UI state
- **Internationalization:** Client-side translation with instant language switching
- **Clean separation:** Backend = domain events, Frontend = presentation
- **HTTP semantics:** Uses status codes instead of duplicating severity
- **Standard library:** react-i18next is the most popular i18n solution for React apps
- **User preference:** Language stored in user profile for consistent experience

## Alternatives Considered

### Backend Sends Fully Rendered Strings
Pros: Simpler for frontend.
Cons: Blocks localization, requires backend deploy for copy changes, duplicates formatting logic.
Why Rejected: Conflicts with internationalization and rapid UX iteration goals.

### Continue Auto-Toast Behavior
Pros: Minimal code changes.
Cons: Duplicated and context-poor messaging; cannot differentiate inline vs global.
Why Rejected: Primary pain point is duplication and lack of contextual control.

### Add Severity & Channel Fields Server-Side
Pros: Backend could influence UX priority.
Cons: Couples presentation concerns to backend; slows experimentation; inconsistent semantics risk.
Why Rejected: Violates separation of concerns.

## Consequences

### Positive
- Reduced duplication and clearer ownership
- Faster iteration on message presentation
- Easier addition of new languages
- Consistent error handling pattern across codebase

### Negative / Trade-offs
- Initial refactor effort across endpoints and hooks
- Need to enforce discipline against reintroducing auto-toasts
- Requires test coverage for missing keys

### Risks & Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Missing translation keys | Medium | Medium | CI check + runtime fallback to key string |
| Overuse of success messages | Low | Medium | Guidelines: prefer optimistic UI for simple success |
| Legacy clients expect old fields | High | Low | Transitional adapter & deprecation notice |
| Nested context objects introduced | Low | Medium | Schema validator + unit tests |

## Success Criteria
- No duplicate toasts in primary user flows post-migration
- 100% new endpoints using standardized `messages` shape
- Zero missing translation key errors in production logs after 30 days
- Adding a language requires only locale file additions
- Form validation errors render inline (not global toasts)

## Change History
| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2024-06-06 | 1.0 | Web Platform Team | Initial version |
| 2024-10-04 | 1.1 | GitHub Copilot | Added alternatives, consequences, risks, success criteria |

## Approval
| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tech Lead | TBD | 2024-06-06 | ✅ |
| Frontend Lead | TBD | 2024-06-06 | ✅ |
| Backend Lead | TBD | 2024-06-06 | ✅ |