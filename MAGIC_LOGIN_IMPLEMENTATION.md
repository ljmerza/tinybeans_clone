# Magic Login Link Implementation

## Overview
This implementation adds passwordless authentication via magic login links to the existing authentication system. Users can request a magic link to be sent to their email, which allows them to log in without entering a password.

## Features

### Backend (Django)

1. **Model: `MagicLoginToken`** (`mysite/auth/models.py`)
   - Stores magic login tokens with expiry tracking
   - Fields:
     - `user`: ForeignKey to User
     - `token`: Unique 64-character token (UUID hex)
     - `is_used`: Boolean flag to prevent reuse
     - `ip_address`: Client IP for audit trail
     - `user_agent`: Browser/client info
     - `expires_at`: Token expiration (15 minutes)
     - `used_at`: Timestamp when token was used
     - `created_at`: Creation timestamp

2. **API Endpoints**
   - `POST /api/auth/magic-login/request/` - Request a magic login link
     - Input: `{ "email": "user@example.com" }`
     - Response: Success message (generic to prevent email enumeration)
     - Rate limited: 5 requests per hour per IP
   
   - `POST /api/auth/magic-login/verify/` - Verify and use a magic login token
     - Input: `{ "token": "abc123..." }`
     - Response: JWT tokens (same as regular login)
     - Rate limited: 10 requests per hour per IP
     - Supports 2FA flow if enabled for the user

3. **Email Template** (`mysite/emails/email_templates/magic_login.email.html`)
   - Professional email with magic link button
   - Clear expiration notice (15 minutes)
   - Security notice about one-time use

4. **Celery Task** (`mysite/auth/tasks.py`)
   - `cleanup_expired_magic_login_tokens()`: Cleans up expired/used tokens older than 7 days
   - Should be scheduled to run daily via Celery Beat

5. **Admin Interface** (`mysite/auth/admin.py`)
   - View and manage magic login tokens
   - Filter by used/unused status
   - Search by user

### Frontend (React/TypeScript)

1. **Updated Login Page** (`web/src/modules/login/routes.login.tsx`)
   - Traditional username/password form (preserved)
   - New "Magic Link" section with:
     - Email input field
     - "Send Magic Login Link" button (disabled until valid email entered)
     - Success/error messages
   - Clean separation with divider ("or")

2. **Magic Login Verification Page** (`web/src/routes/magic-login.tsx`)
   - Automatically extracts token from URL query parameter
   - Shows loading state while verifying
   - Success state with redirect
   - Error state with "Return to Login" button
   - Handles 2FA flow if required

3. **API Hooks** (`web/src/modules/login/hooks.ts`)
   - `useMagicLoginRequest()`: Request magic link
   - `useMagicLoginVerify()`: Verify and authenticate with token
   - Integrated with existing auth flow and 2FA

4. **Type Definitions** (`web/src/modules/login/types.ts`)
   - `MagicLoginRequest`
   - `MagicLoginRequestResponse`
   - `MagicLoginVerifyRequest`
   - `MagicLoginVerifyResponse`

## Security Features

1. **Token Security**
   - Cryptographically secure UUID tokens (64 characters)
   - Single-use only (marked as used after verification)
   - Short expiration (15 minutes)
   - Unique database constraint prevents duplicates

2. **Rate Limiting**
   - Request endpoint: 5/hour per IP
   - Verify endpoint: 10/hour per IP
   - Prevents brute force and abuse

3. **Email Enumeration Prevention**
   - Always returns success message, even if email doesn't exist
   - Prevents attackers from discovering valid email addresses

4. **Audit Trail**
   - IP address and user agent stored with each token
   - Timestamp tracking (created, used)
   - Admin visibility for security monitoring

5. **2FA Integration**
   - Magic login respects 2FA settings
   - Trusted device check applied
   - Same 2FA flow as password login

## User Flow

### Requesting Magic Link
1. User navigates to login page
2. Enters email in "Magic Link" section
3. Clicks "Send Magic Login Link"
4. Receives email with magic link (if account exists)

### Using Magic Link
1. User clicks link in email
2. Redirected to `/magic-login?token=...`
3. Token automatically verified
4. If valid and no 2FA: User logged in and redirected to home
5. If valid with 2FA: User redirected to 2FA verification
6. If invalid/expired: Error shown with option to return to login

## Database Migration

Migration file created: `mysite/auth/migrations/0006_magiclogintoken.py`

To apply:
```bash
cd mysite
python manage.py migrate auth
```

## Email Template Setup

The magic login email template is automatically registered via:
- Template ID: `'users.magic.login'`
- File: `mysite/emails/email_templates/magic_login.email.html`

No additional configuration needed if email sending is already configured.

## Celery Task Schedule (Optional)

Add to your Celery Beat schedule to clean up old tokens:

```python
# mysite/mysite/celery.py or settings
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # ... other tasks
    'cleanup-expired-magic-tokens': {
        'task': 'auth.tasks.cleanup_expired_magic_login_tokens',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}
```

## Testing

### Backend Testing
```bash
cd mysite
python manage.py test auth.tests.test_magic_login  # (if tests created)
```

### Manual Testing
1. Start backend: `cd mysite && python manage.py runserver`
2. Start frontend: `cd web && npm run dev`
3. Navigate to login page
4. Enter email and request magic link
5. Check email/logs for magic link
6. Click link to verify login

### API Testing with curl
```bash
# Request magic link
curl -X POST http://localhost:8000/api/auth/magic-login/request/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{"email": "user@example.com"}'

# Verify token
curl -X POST http://localhost:8000/api/auth/magic-login/verify/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{"token": "abc123..."}'
```

## Compatibility

- **Preserves existing authentication**: Traditional username/password login still works
- **2FA compatible**: Fully integrated with existing 2FA system
- **Trusted devices**: Works with "Remember Me" feature
- **Email system**: Uses existing email infrastructure

## Future Enhancements

Potential improvements:
1. Configurable token expiry time
2. User preference to enable/disable magic links
3. Email templates for different locales
4. Magic link usage statistics/analytics
5. Option to send magic link to alternate verified email
6. QR code generation for mobile scanning

## Files Modified/Created

### Backend
- Modified:
  - `mysite/auth/models.py` - Added MagicLoginToken model
  - `mysite/auth/serializers.py` - Added magic login serializers
  - `mysite/auth/views.py` - Added magic login views
  - `mysite/auth/urls.py` - Added magic login endpoints
  - `mysite/auth/admin.py` - Added admin for magic login tokens
  - `mysite/auth/tasks.py` - Added cleanup task
  - `mysite/emails/templates.py` - Added magic login template ID

- Created:
  - `mysite/emails/email_templates/magic_login.email.html` - Email template
  - `mysite/auth/migrations/0006_magiclogintoken.py` - Database migration

### Frontend
- Modified:
  - `web/src/modules/login/routes.login.tsx` - Updated login page UI
  - `web/src/modules/login/hooks.ts` - Added magic login hooks
  - `web/src/modules/login/types.ts` - Added magic login types

- Created:
  - `web/src/routes/magic-login.tsx` - Magic login verification page
  - `web/src/modules/login/routes.magic-login.tsx` - (alternative, can be removed)

## Support

For issues or questions:
1. Check logs: Django logs for backend issues
2. Check browser console: React for frontend issues
3. Verify email sending is configured correctly
4. Ensure database migrations are applied
5. Check rate limiting if requests are blocked
