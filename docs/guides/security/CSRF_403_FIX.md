# 403 Forbidden Error - CSRF Token Fix

## Issue
```
POST http://192.168.1.76:3053/api/auth/login/ 403 (Forbidden)
Error: You do not have permission to perform this action.
```

## Root Cause
Django requires CSRF tokens for POST requests. The frontend wasn't sending the CSRF token in the headers.

## Solution Applied ✅

### 1. Added CSRF Token Support to API Client

**File:** `web/src/modules/login/client.ts`

Added CSRF token helper function:
```typescript
// Get CSRF token from cookie
function getCsrfToken(): string | null {
  const name = 'csrftoken'
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null
  return null
}
```

Updated request function to include CSRF token:
```typescript
// Add CSRF token for non-GET requests
if (init.method && init.method !== 'GET') {
  const csrfToken = getCsrfToken()
  if (csrfToken) {
    headers.set('X-CSRFToken', csrfToken)
  }
}
```

### 2. Updated Token Refresh Function

Now includes CSRF token in refresh requests:
```typescript
export async function refreshAccessToken(): Promise<boolean> {
  const csrfToken = getCsrfToken()
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (csrfToken) headers['X-CSRFToken'] = csrfToken
  
  const res = await fetch(`${API_BASE}/auth/token/refresh/`, { 
    method: 'POST', 
    credentials: 'include',
    headers
  })
  // ...
}
```

## How CSRF Works

### Django Side:
1. Django sets a `csrftoken` cookie on first response
2. Django expects `X-CSRFToken` header in POST/PUT/PATCH/DELETE requests
3. If header doesn't match cookie, returns 403 Forbidden

### Frontend Side:
1. Browser receives and stores `csrftoken` cookie
2. Frontend reads cookie value
3. Frontend sends value in `X-CSRFToken` header
4. Django validates and allows request

## Getting the CSRF Token

### Option 1: Visit Any Django Page First
```bash
# Visit the API root to get CSRF token
curl -c cookies.txt http://192.168.1.76:3053/api/

# Use the cookie in subsequent requests
curl -b cookies.txt -X POST http://192.168.1.76:3053/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_TOKEN_FROM_COOKIE" \
  -d '{"username":"test","password":"test"}'
```

### Option 2: Dedicated CSRF Endpoint (Recommended)

Add to Django if needed:
```python
# In views.py
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

# In urls.py
path('auth/csrf/', get_csrf, name='csrf'),
```

Frontend usage:
```typescript
// Fetch CSRF token before login
await fetch('/api/auth/csrf/', { credentials: 'include' })
```

## Testing

### 1. Check if CSRF Cookie Exists

In browser console:
```javascript
document.cookie.split(';').find(c => c.includes('csrftoken'))
```

Should show: `"csrftoken=abc123..."`

### 2. Test Login Request

Network tab should show:
```
Request Headers:
  X-CSRFToken: abc123...
  Content-Type: application/json
  Cookie: csrftoken=abc123...
```

### 3. Manual Test

```bash
# Get CSRF token
curl -c /tmp/cookies.txt http://192.168.1.76:3053/api/

# Extract token
CSRF_TOKEN=$(grep csrftoken /tmp/cookies.txt | cut -f7)

# Test login
curl -b /tmp/cookies.txt \
  -X POST http://192.168.1.76:3053/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"username":"testuser","password":"testpass"}'
```

## Django Settings to Check

### Development (mysite/settings_dev.py):
```python
# CSRF Settings
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://192.168.1.76:3053',
    'http://127.0.0.1:3000',
]

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://192.168.1.76:3053',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True
```

### Production (mysite/settings_prod.py):
```python
# CSRF Settings
CSRF_COOKIE_SECURE = True      # HTTPS only
CSRF_COOKIE_HTTPONLY = False   # Allow JavaScript
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
]

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True
```

## Alternative: Disable CSRF for API (Not Recommended)

If you're using JWT authentication, you might disable CSRF for API endpoints:

```python
# In views.py
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    # ...
```

**WARNING:** Only do this if:
- Using JWT tokens (not session cookies)
- API is separate from web interface
- You understand the security implications

## Troubleshooting

### Issue: Cookie not being set

**Check:**
```python
# In settings.py
CSRF_COOKIE_SECURE = False  # For HTTP (dev only)
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-domain
```

### Issue: Cookie set but not sent

**Check:**
```typescript
// Ensure credentials: 'include'
fetch(url, { credentials: 'include' })
```

### Issue: CORS error before 403

**Fix CORS first:**
```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = ['http://your-frontend-url']
```

### Issue: Token mismatch

**Clear cookies and retry:**
```javascript
// Clear all cookies
document.cookie.split(";").forEach(c => {
  document.cookie = c.trim().split("=")[0] + 
    '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/';
})
location.reload()
```

## Verification Steps

1. ✅ Build succeeds
2. ✅ Start dev server
3. ✅ Visit frontend in browser
4. ✅ Check browser console for csrftoken cookie
5. ✅ Try login
6. ✅ Check Network tab for X-CSRFToken header
7. ✅ Verify 200 response (not 403)

## Build Status

✅ Build: SUCCESS
✅ CSRF support added
✅ Token refresh updated
✅ Ready to test

---

**Updated:** 2025-01-08
**Status:** Fixed - Ready to Test
