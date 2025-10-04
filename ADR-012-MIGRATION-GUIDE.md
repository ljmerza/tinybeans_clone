# ADR-012 Migration Guide

This guide provides step-by-step instructions for migrating existing code to use the new notification strategy.

## Overview

The migration involves:
1. Backend: Update views to use `notification_utils`
2. Frontend: Update components to use `modernAuthClient` and `useApiMessages`
3. Add translation keys for all user-facing messages

## Migration Priority

### Phase 1: High-Traffic Endpoints (Week 1-2)
- [ ] Login/Signup
- [ ] Password reset
- [ ] Profile updates
- [ ] 2FA flows

### Phase 2: Medium-Traffic Endpoints (Week 3-4)
- [ ] Circle management
- [ ] Media uploads
- [ ] Notification preferences
- [ ] Child/Pet profiles

### Phase 3: Low-Traffic Endpoints (Week 5-6)
- [ ] Email verification
- [ ] OAuth flows
- [ ] Admin operations
- [ ] Cleanup old code

## Backend Migration

### Step 1: Import New Utilities

```python
# Old imports
from .response_utils import error_response, success_response

# New imports
from mysite.notification_utils import (
    create_message,
    success_response,
    error_response,
    validation_error_response,
    rate_limit_response
)
```

### Step 2: Update Success Responses

**Before:**
```python
data = UserSerializer(user).data
data['message'] = 'Account created successfully'
return Response(data, status=status.HTTP_201_CREATED)
```

**After:**
```python
user_data = UserSerializer(user).data
return success_response(
    user_data,
    messages=[create_message('notifications.auth.signup_success')],
    status_code=status.HTTP_201_CREATED
)
```

### Step 3: Update Error Responses

**Before:**
```python
return Response(
    {'error': 'File is too large'},
    status=status.HTTP_400_BAD_REQUEST
)
```

**After:**
```python
return error_response(
    'file_too_large',
    [create_message('errors.file_too_large', {
        'filename': file.name,
        'maxSize': '10MB'
    })],
    status.HTTP_400_BAD_REQUEST
)
```

### Step 4: Update Validation Errors

**Before:**
```python
return Response(
    {
        'email': ['Invalid email address'],
        'password': ['Password too short']
    },
    status=status.HTTP_400_BAD_REQUEST
)
```

**After:**
```python
return validation_error_response([
    create_message('errors.email_invalid', {'field': 'email'}),
    create_message('errors.password_too_short', {
        'field': 'password',
        'minLength': 8
    })
])
```

### Step 5: Add Translation Keys

For each i18n_key used, add entries to both translation files:

**web/src/i18n/locales/en.json:**
```json
{
  "errors": {
    "file_too_large": "File {{filename}} is too large. Maximum size is {{maxSize}}."
  }
}
```

**web/src/i18n/locales/es.json:**
```json
{
  "errors": {
    "file_too_large": "El archivo {{filename}} es demasiado grande. El tamaño máximo es {{maxSize}}."
  }
}
```

## Frontend Migration

### Step 1: Update Imports

**Before:**
```typescript
import { api } from '@/features/auth/api/authClient';
```

**After:**
```typescript
import { apiClient } from '@/features/auth/api/modernAuthClient';
import { useApiMessages } from '@/i18n';
```

### Step 2: Update Hooks

**Before:**
```typescript
export function useLogin() {
  return useMutation({
    mutationFn: (body) => api.post('/auth/login/', body),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access);
      // Auto-toast handles success message
    },
  });
}
```

**After:**
```typescript
export function useLoginModern() {
  const { showAsToast } = useApiMessages();
  
  return useMutation({
    mutationFn: (body) => apiClient.post('/auth/login/', body),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access);
      
      // Explicitly show success message if needed
      if (data.messages) {
        showAsToast(data.messages, 200);
      }
    },
  });
}
```

### Step 3: Update Components - Simple Toast

For background operations, show messages as toast:

**Before:**
```typescript
function MyComponent() {
  const syncMutation = useMutation({
    mutationFn: () => api.post('/sync/', {}),
  });
  
  return <button onClick={() => syncMutation.mutate()}>Sync</button>;
}
```

**After:**
```typescript
function MyComponent() {
  const { showAsToast } = useApiMessages();
  
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/sync/', {}),
    onSuccess: (data) => {
      if (data.messages) {
        showAsToast(data.messages, 200);
      }
    },
    onError: (error: any) => {
      if (error.messages) {
        showAsToast(error.messages, error.status || 400);
      }
    },
  });
  
  return <button onClick={() => syncMutation.mutate()}>Sync</button>;
}
```

### Step 4: Update Components - Form Validation

For forms, show errors inline:

**Before:**
```typescript
function LoginForm() {
  const login = useLogin();
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Fields */}
      {login.error && <div>{login.error.message}</div>}
    </form>
  );
}
```

**After:**
```typescript
function LoginForm() {
  const login = useLoginModern();
  const { getGeneral } = useApiMessages();
  const [generalError, setGeneralError] = useState('');
  
  const handleSubmit = async (data) => {
    setGeneralError('');
    try {
      await login.mutateAsync(data);
    } catch (error: any) {
      const generalErrors = getGeneral(error.messages);
      if (generalErrors.length > 0) {
        setGeneralError(generalErrors.join('. '));
      } else {
        setGeneralError(error.message ?? 'Operation failed');
      }
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Fields */}
      {generalError && <div className="error">{generalError}</div>}
    </form>
  );
}
```

### Step 5: Update Components - Field Errors

For field-level validation:

```typescript
function ProfileForm() {
  const { getFieldErrors, getGeneral } = useApiMessages();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState('');
  
  const handleSubmit = async (data) => {
    setFieldErrors({});
    setGeneralError('');
    
    try {
      await apiClient.patch('/profile/', data);
      // Success - navigate or show inline feedback
    } catch (error: any) {
      // Extract field errors
      const errors = getFieldErrors(error.messages);
      setFieldErrors(errors);
      
      // Extract general errors
      const general = getGeneral(error.messages);
      if (general.length > 0) {
        setGeneralError(general.join('. '));
      }
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input name="email" />
        {fieldErrors.email && <span className="error">{fieldErrors.email}</span>}
      </div>
      
      <div>
        <input name="password" />
        {fieldErrors.password && <span className="error">{fieldErrors.password}</span>}
      </div>
      
      {generalError && <div className="error">{generalError}</div>}
      
      <button type="submit">Save</button>
    </form>
  );
}
```

## Testing Migration

### Backend Tests

Update tests to check new response format:

```python
def test_error_response_format(self):
    response = self.client.post('/api/endpoint/', invalid_data)
    
    self.assertEqual(response.status_code, 400)
    self.assertIn('error', response.data)
    self.assertIn('messages', response.data)
    
    messages = response.data['messages']
    self.assertEqual(len(messages), 1)
    self.assertEqual(messages[0]['i18n_key'], 'errors.validation_failed')
```

### Frontend Tests

Update tests to handle messages:

```typescript
it('should display error messages', async () => {
  const mockError = {
    messages: [
      { i18n_key: 'errors.email_invalid', context: { field: 'email' } }
    ],
    status: 400
  };
  
  // Mock API call to return error
  apiClient.post = jest.fn().mockRejectedValue(mockError);
  
  // Render component and submit
  // Assert error is displayed
});
```

## Rollback Plan

If issues arise, the migration can be rolled back:

1. **Backend**: Old `response_utils.py` still exists, revert imports
2. **Frontend**: Old `authClient` with auto-toast still works, revert imports
3. **Database**: Language field is optional, no data loss

## Common Issues

### Issue 1: Missing Translation Keys

**Symptom:** Keys displayed instead of translated text
**Fix:** Add keys to both en.json and es.json

### Issue 2: Messages Not Displayed

**Symptom:** Success/error messages don't appear
**Fix:** Ensure component calls `showAsToast()` or displays messages inline

### Issue 3: Duplicate Messages

**Symptom:** Same message shown twice
**Fix:** Check for old auto-toast behavior, use `modernAuthClient`

### Issue 4: Context Not Interpolating

**Symptom:** Variables show as {{var}} instead of values
**Fix:** Ensure context is flat object, check translation file syntax

## Checklist

### Backend Endpoint Migration
- [ ] Import `notification_utils`
- [ ] Replace `Response()` with `success_response()` or `error_response()`
- [ ] Use `create_message()` for all user-facing text
- [ ] Add i18n keys to translation files
- [ ] Update tests
- [ ] Test manually

### Frontend Component Migration
- [ ] Import `modernAuthClient` and `useApiMessages`
- [ ] Update mutation hooks
- [ ] Handle messages explicitly (toast or inline)
- [ ] Remove reliance on auto-toast
- [ ] Update tests
- [ ] Test manually

### Translation Keys
- [ ] Add to en.json
- [ ] Add to es.json
- [ ] Test language switching
- [ ] Verify context interpolation

## Timeline

- **Week 1-2:** Migrate authentication flows (login, signup, password reset)
- **Week 3-4:** Migrate core features (profile, circles, media)
- **Week 5-6:** Migrate remaining endpoints and clean up
- **Week 7:** Testing, bug fixes, documentation updates
- **Week 8:** Remove deprecated code (old authClient, response_utils)

## Support

For questions or issues during migration:
- Review: `ADR-012-QUICK-REFERENCE.md`
- Examples: `web/src/i18n/EXAMPLES.tsx`
- Backend docs: `mysite/mysite/NOTIFICATION_UTILS_README.md`
- Frontend docs: `web/src/i18n/README.md`
