# ADR-012: Notification Strategy - Implementation Complete ✅

This directory contains the complete implementation of ADR-012: Notification Strategy, which establishes a standardized approach for backend messages with frontend presentation control and internationalization support.

## Quick Links

📋 **Start Here:**
- [Complete Status Report](./ADR-012-COMPLETE-STATUS.md) - Full implementation overview
- [Quick Reference Guide](./ADR-012-QUICK-REFERENCE.md) - Daily reference for developers
- [Migration Guide](./ADR-012-MIGRATION-GUIDE.md) - Step-by-step migration instructions

📚 **Documentation:**
- [Backend Documentation](./mysite/mysite/NOTIFICATION_UTILS_README.md) - API reference for backend utilities
- [Frontend Documentation](./web/src/i18n/README.md) - API reference for frontend i18n
- [Original ADR](./docs/architecture/adr/ADR-012-NOTIFICATION-STRATEGY.md) - Full architectural decision

💻 **Code Examples:**
- [Frontend Examples](./web/src/i18n/EXAMPLES.tsx) - Common usage patterns
- [Modern Login Component](./web/src/features/auth/components/ModernLoginCard.tsx) - Complete example
- [Language Switcher](./web/src/components/LanguageSwitcher.tsx) - Language selection UI

## What Is ADR-012?

ADR-012 establishes a notification strategy where:
- **Backend** sends i18n keys + context (not translated text)
- **Frontend** translates and decides when/how to display messages
- **Users** can choose their preferred language
- **Developers** have clear patterns for message handling

### Key Benefits
✅ No duplicate notifications  
✅ Context-aware display (toast vs inline)  
✅ Instant language switching  
✅ Clean separation of concerns  
✅ Type-safe implementation  

## For Backend Developers

### Quick Example
```python
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

📖 [Read Backend Documentation →](./mysite/mysite/NOTIFICATION_UTILS_README.md)

## For Frontend Developers

### Quick Example
```typescript
import { useApiMessages } from '@/i18n';

function MyComponent() {
  const { handleError } = useApiMessages();
  
  try {
    await apiClient.post('/endpoint/', data);
  } catch (error) {
    const fieldErrors = handleError(error);
    // Use fieldErrors in form
  }
}
```

📖 [Read Frontend Documentation →](./web/src/i18n/README.md)

## Implementation Status

### Completed ✅
- Backend notification utilities
- Frontend i18n infrastructure  
- React hooks and components
- Language switcher UI
- Comprehensive documentation
- Example code and patterns
- Migration guides
- 10/10 backend tests passing

### Ready for Use ✅
- `mysite.notification_utils` - Backend response utilities
- `@/i18n` - Frontend i18n module
- `modernAuthClient` - ADR-012 compliant HTTP client
- Modern auth hooks
- Translation files (English, Spanish)

## Getting Started

### 1. Backend: Use New Response Format
```python
from mysite.notification_utils import success_response, create_message

return success_response(
    {'user_id': user.id},
    messages=[create_message('notifications.profile.updated')]
)
```

### 2. Frontend: Handle Messages Explicitly
```typescript
import { useApiMessages } from '@/i18n';
import { apiClient } from '@/features/auth/api/modernAuthClient';

const { showAsToast } = useApiMessages();

try {
  const response = await apiClient.post('/sync/', {});
  showAsToast(response.messages, 200);
} catch (error) {
  showAsToast(error.messages, error.status);
}
```

### 3. Add Translation Keys
**web/src/i18n/locales/en.json:**
```json
{
  "notifications": {
    "profile": {
      "updated": "Profile updated successfully"
    }
  }
}
```

**web/src/i18n/locales/es.json:**
```json
{
  "notifications": {
    "profile": {
      "updated": "Perfil actualizado exitosamente"
    }
  }
}
```

## Migration Strategy

The implementation is backward compatible:
- Old `authClient` with auto-toast → Still works
- New `modernAuthClient` without auto-toast → Available now
- Migrate components gradually over 6-8 weeks
- Follow the [Migration Guide](./ADR-012-MIGRATION-GUIDE.md)

## Running Tests

### Backend Tests (Passing ✅)
```bash
cd /media/cubxi/docker/projects/tinybeans_copy
python -m pytest mysite/mysite/tests/test_notification_utils.py -v
```

Result: **10/10 tests passing**

### Database Migration
```bash
python mysite/manage.py migrate
```

## File Structure

```
Project Root
├── ADR-012-COMPLETE-STATUS.md      # Complete implementation report
├── ADR-012-QUICK-REFERENCE.md      # Developer quick reference
├── ADR-012-MIGRATION-GUIDE.md      # Migration instructions
│
├── mysite/                          # Backend
│   ├── mysite/
│   │   ├── notification_utils.py   # Response utilities
│   │   ├── NOTIFICATION_UTILS_README.md
│   │   └── tests/
│   │       └── test_notification_utils.py (10/10 passing ✅)
│   ├── users/
│   │   ├── models/user.py          # Added language field
│   │   ├── migrations/0008_add_language_field.py
│   │   └── serializers/            # Updated with language
│   └── auth/
│       └── views.py                # Migrated to new format
│
└── web/                             # Frontend
    └── src/
        ├── i18n/                    # i18n module
        │   ├── config.ts
        │   ├── notificationUtils.ts
        │   ├── useApiMessages.ts
        │   ├── EXAMPLES.tsx
        │   ├── README.md
        │   └── locales/
        │       ├── en.json
        │       └── es.json
        ├── features/auth/
        │   ├── api/modernAuthClient.ts
        │   ├── hooks/modernHooks.ts
        │   └── components/ModernLoginCard.tsx
        └── components/
            └── LanguageSwitcher.tsx
```

## Common Tasks

### Add a New Error Message
1. Choose i18n key: `errors.my_new_error`
2. Add to `web/src/i18n/locales/en.json` and `es.json`
3. Use in backend: `create_message('errors.my_new_error', context)`

### Add a New Language
1. Create `web/src/i18n/locales/fr.json`
2. Add to `web/src/i18n/config.ts` resources
3. Add to `Language` enum in backend `user.py`

### Migrate an Endpoint
1. Update backend view to use `notification_utils`
2. Update frontend hook/component to use `modernAuthClient`
3. Add translation keys
4. Test both success and error cases

## Support & Resources

📖 **Documentation**
- [Quick Reference](./ADR-012-QUICK-REFERENCE.md) - For daily use
- [Migration Guide](./ADR-012-MIGRATION-GUIDE.md) - For updating code
- [Status Report](./ADR-012-COMPLETE-STATUS.md) - Implementation details

💻 **Code Examples**
- [Frontend Examples](./web/src/i18n/EXAMPLES.tsx)
- [Backend Examples](./mysite/mysite/NOTIFICATION_UTILS_README.md)

🧪 **Testing**
- Backend: `pytest mysite/mysite/tests/test_notification_utils.py`
- Coverage: 10/10 tests passing ✅

## Success Criteria

From ADR-012, we will measure success by:
- [ ] No duplicate toasts in primary user flows
- [x] 100% new endpoints using standardized format
- [ ] Zero missing translation key errors in production
- [x] Adding a language requires only locale file additions
- [ ] Form validation errors render inline

*Checkboxes with [x] are complete, [ ] require running application to verify*

## Timeline

**Completed:** December 2024
- ✅ Core infrastructure
- ✅ Backend utilities
- ✅ Frontend i18n
- ✅ Documentation
- ✅ Examples
- ✅ Tests

**Next Steps:**
1. Team review
2. Phase 1 migration (high-traffic endpoints)
3. Phase 2 migration (remaining endpoints)
4. Cleanup deprecated code

## Questions?

- Review the [Quick Reference](./ADR-012-QUICK-REFERENCE.md)
- Check the [Examples](./web/src/i18n/EXAMPLES.tsx)
- Read the [Migration Guide](./ADR-012-MIGRATION-GUIDE.md)
- Consult the [Complete Status Report](./ADR-012-COMPLETE-STATUS.md)

---

**Status:** ✅ Implementation Complete  
**Tests:** ✅ 10/10 Passing  
**Documentation:** ✅ Complete  
**Ready for:** Team Review & Migration
