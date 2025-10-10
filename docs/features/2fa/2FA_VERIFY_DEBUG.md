# 2FA Verification Not Redirecting - Debug Guide

## Issue
After calling `/auth/2fa/verify-login/` with correct code, the response is success but doesn't redirect to home page.

## Debug Logging Added ✅

### Location 1: `web/src/features/twofa/hooks.ts`
**useVerify2FALogin hook now logs:**
- ✅ Full verification response
- ✅ Access token (first 20 chars)
- ✅ Trusted device status
- ✅ Navigation attempt
- ✅ Any errors

### Location 2: `web/src/routes/profile/2fa/verify.tsx`
**Verification page now logs:**
- ✅ When verify button is clicked
- ✅ Code being sent

## Testing Steps

### 1. Open Browser Console
Press `F12` or right-click → Inspect → Console tab

### 2. Login with 2FA Account
Should navigate to `/profile/2fa/verify`

### 3. Enter Your 2FA Code
Watch console for these logs in order:

```
Expected Console Output:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. "Verifying 2FA code..."
2. "2FA verify success: { user: {...}, tokens: {...} }"
3. "Setting access token: eyJ0eXAiOiJKV1QiLCJh..."
4. "Navigating to home page"
```

### 4. Check What You Actually See

#### ✅ Good Case - Working:
```javascript
Verifying 2FA code...
2FA verify success: {
  user: { id: 1, username: "...", email: "..." },
  tokens: { access: "eyJ..." },
  trusted_device: false
}
Setting access token: eyJ0eXAiOiJKV1QiLCJh...
Navigating to home page
// Should redirect to / now
```

#### ❌ Bad Case - Token Missing:
```javascript
Verifying 2FA code...
2FA verify success: { ... }
No access token in response: { ... }
Navigating to home page
// May redirect but not logged in
```

#### ❌ Bad Case - Error:
```javascript
Verifying 2FA code...
2FA verify error: Error: Invalid code
// Stays on verification page
```

## Troubleshooting

### Issue: "No access token in response"

**Check Backend Response:**
```bash
# Test the verify endpoint directly
curl -X POST http://localhost:8000/auth/2fa/verify-login/ \
  -H "Content-Type: application/json" \
  -d '{
    "partial_token": "YOUR_PARTIAL_TOKEN",
    "code": "123456",
    "remember_me": false
  }' | python -m json.tool
```

**Expected Response:**
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  },
  "trusted_device": false
}
```

**If backend response is correct but frontend doesn't see it:**
- Check Network tab in DevTools
- Look for `/auth/2fa/verify-login/` request
- Check Response tab - does it have tokens?
- Check if any error transforming response

### Issue: "Navigating to home page" but stays on /profile/2fa/verify

**Possible Causes:**

1. **Router Navigation Blocked**
   ```javascript
   // Check if there's a route guard
   // Check browser console for navigation errors
   ```

2. **State Not Clearing**
   ```javascript
   // Try manually navigating
   window.location.href = '/'
   ```

3. **Token Not Being Saved**
   ```javascript
   // Check in console
   import { authStore } from '@/features/auth/store'
   console.log(authStore.state.accessToken)
   ```

### Issue: Navigates but shows as logged out

**Check Token Storage:**
```javascript
// In browser console
import { authStore } from '@/features/auth/store'
console.log('Token:', authStore.state.accessToken)

// Check localStorage
console.log('LocalStorage:', localStorage)
```

**If token is null:**
- setAccessToken() didn't work
- Check if store is configured correctly
- Try manually: `authStore.state.accessToken = "your_token"`

### Issue: "2FA verify error" in console

**Check Error Details:**
```javascript
// Error will be logged
// Common errors:
// - "Invalid code" = wrong 6-digit code
// - "Invalid or expired partial token" = partial token issue
// - "Network error" = backend not responding
```

## Manual Testing

### Test 1: Check API Call
```javascript
// In browser console after getting partial token
const response = await fetch('http://localhost:8000/auth/2fa/verify-login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    partial_token: 'YOUR_PARTIAL_TOKEN',
    code: '123456',
    remember_me: false
  })
})
const data = await response.json()
console.log(data)
```

### Test 2: Check Token Storage
```javascript
// After verification attempt
import { authStore } from '@/features/auth/store'
console.log('Current token:', authStore.state.accessToken)

// Try setting manually
import { setAccessToken } from '@/features/auth/store'
setAccessToken('test_token_123')
console.log('After manual set:', authStore.state.accessToken)
```

### Test 3: Check Navigation
```javascript
// Try manual navigation
import { useNavigate } from '@tanstack/react-router'
const navigate = useNavigate()
navigate({ to: '/' })

// Or direct
window.location.href = '/'
```

## Common Solutions

### Solution 1: Response Format Mismatch

**If backend returns different format:**

Update type definition in `web/src/features/twofa/types.ts`:
```typescript
export interface TwoFactorVerifyLoginResponse {
  user: {
    id: number
    username: string
    email: string
  }
  tokens: {
    access: string
  }
  trusted_device: boolean
}
```

### Solution 2: Token Not Persisting

**Check if store is initialized:**

In `web/src/features/auth/store.ts`:
```typescript
export const authStore = new Store({
  accessToken: null as string | null,
})

export function setAccessToken(token: string | null) {
  authStore.setState(() => ({ accessToken: token }))
}
```

### Solution 3: Navigation Not Working

**Add fallback navigation:**

In `web/src/features/twofa/hooks.ts`:
```typescript
onSuccess: (data) => {
  setAccessToken(data.tokens.access)
  
  // Try navigate
  navigate({ to: '/' })
  
  // Fallback after 100ms
  setTimeout(() => {
    if (window.location.pathname !== '/') {
      window.location.href = '/'
    }
  }, 100)
}
```

## Verification Checklist

After entering code, verify:

- [ ] Console shows "Verifying 2FA code..."
- [ ] Console shows "2FA verify success: {...}"
- [ ] Response has `tokens.access`
- [ ] Console shows "Setting access token: ..."
- [ ] Console shows "Navigating to home page"
- [ ] URL changes to `/`
- [ ] Home page content loads
- [ ] User appears logged in

## Network Tab Debugging

1. Open DevTools → Network tab
2. Filter by "verify-login"
3. Enter code and submit
4. Click on the request
5. Check:
   - **Status:** Should be 200
   - **Response:** Should have tokens.access
   - **Headers:** Should have Set-Cookie for refresh token

## Backend Logs

Check Django console for:
```
[timestamp] "POST /auth/2fa/verify-login/ HTTP/1.1" 200
```

If 400 or 401:
- Check partial token validity
- Check code correctness
- Check backend logs for error details

## Quick Fixes

### Reset Everything:
```javascript
// Clear all storage
localStorage.clear()
sessionStorage.clear()

// Clear cookies (in console)
document.cookie.split(";").forEach(c => {
  document.cookie = c.trim().split("=")[0] + 
    '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/';
})

// Reload
window.location.reload()
```

### Force Token and Navigate:
```javascript
// Manually set token from backend response
import { setAccessToken } from '@/features/auth/store'
setAccessToken('YOUR_ACCESS_TOKEN_HERE')

// Navigate
window.location.href = '/'
```

## What to Report

If still not working, provide:

1. **Console logs:** Copy all logs after clicking verify
2. **Network response:** Screenshot of verify-login response
3. **Current URL:** Before and after verification
4. **Token state:** `authStore.state.accessToken` value
5. **Any errors:** Red errors in console

---

**Updated:** 2025-01-08
**Status:** Debugging Added
