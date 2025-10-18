# ADR-005: CSRF Token Management for Authentication

## Status
Implemented

## Context

The Tinybeans application uses Django REST Framework for the backend API and React (with TanStack Router/Query) for the frontend. Django enforces CSRF (Cross-Site Request Forgery) protection for state-changing operations (POST, PUT, PATCH, DELETE requests) by default. The frontend needs to obtain and properly send CSRF tokens with authenticated requests to prevent 403 Forbidden errors.

### Security Requirements

1. Protect against CSRF attacks on all state-changing endpoints
2. Work seamlessly with JWT-based authentication
3. Handle token refresh scenarios
4. Support both session-based and token-based authentication patterns
5. Maintain CORS compatibility for local development and production

### Technical Constraints

- Django REST Framework with CSRF middleware enabled
- React frontend with TanStack Router/Query
- JWT tokens stored in localStorage (access token) and httpOnly cookies (refresh token)
- Development environment runs on different ports (frontend: 3000, backend: 3053)
- Production environment serves frontend and backend from same domain

## Decision

We have implemented a **Dedicated CSRF Endpoint with Pre-initialization** approach for CSRF token management.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Application                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  main.tsx (App Bootstrap)                              │ │
│  │  1. Call ensureCsrfToken() on app load                 │ │
│  │  2. Try refreshAccessToken()                           │ │
│  │  3. Render app                                         │ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                         │
│  ┌─────────────────▼──────────────────────────────────────┐ │
│  │  lib/csrf.ts                                           │ │
│  │  - ensureCsrfToken(): Fetch /auth/csrf/               │ │
│  │  - Caches initialization state                         │ │
│  │  - Sets csrftoken cookie                              │ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                         │
│  ┌─────────────────▼──────────────────────────────────────┐ │
│  │  features/auth/client.ts                               │ │
│  │  - getCsrfToken(): Read from document.cookie          │ │
│  │  - Add X-CSRFToken header to all POST/PUT/PATCH/DELETE│ │
│  │  - Include credentials in all requests                │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP Request
                            │ Cookie: csrftoken=abc123...
                            │ X-CSRFToken: abc123...
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Django Backend                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  auth/urls.py                                          │ │
│  │  path('csrf/', get_csrf_token)                         │ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                         │
│  ┌─────────────────▼──────────────────────────────────────┐ │
│  │  auth/views.py                                         │ │
│  │  @ensure_csrf_cookie                                   │ │
│  │  def get_csrf_token(request):                          │ │
│  │      return JsonResponse({'detail': 'CSRF cookie set'})│ │
│  └────────────────────────────────────────────────────────┘ │
│                    │                                         │
│                    ▼                                         │
│  Sets Cookie: csrftoken=abc123...; HttpOnly=False; SameSite │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### 1. Backend: Dedicated CSRF Endpoint

**File:** `mysite/auth/views.py`

```python
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Endpoint to set CSRF cookie for the frontend.
    Call this endpoint before making any POST requests to get the CSRF token.
    """
    return JsonResponse({'detail': 'CSRF cookie set'})
```

**File:** `mysite/auth/urls.py`

```python
urlpatterns = [
    path('csrf/', get_csrf_token, name='auth-csrf'),
    # ... other routes
]
```

**Rationale:**
- Explicit endpoint for CSRF token initialization
- Uses `@ensure_csrf_cookie` decorator to guarantee cookie is set
- Simple GET request (no side effects)
- Can be called multiple times safely (idempotent)
- Returns 200 OK with confirmation message

#### 2. Frontend: CSRF Utility Module

**File:** `web/src/lib/csrf.ts`

```typescript
import { API_BASE } from '@/features/auth/client'

let csrfInitialized = false

/**
 * Initialize CSRF token by fetching from backend
 * This ensures the csrftoken cookie is set
 */
export async function ensureCsrfToken(): Promise<void> {
  if (csrfInitialized) return

  try {
    await fetch(`${API_BASE}/auth/csrf/`, {
      method: 'GET',
      credentials: 'include',
    })
    csrfInitialized = true
    console.log('CSRF token initialized')
  } catch (error) {
    console.error('Failed to initialize CSRF token:', error)
    // Don't throw - let the actual API call fail with proper error
  }
}

/**
 * Reset CSRF initialization state
 * Useful for testing or after logout
 */
export function resetCsrfState(): void {
  csrfInitialized = false
}
```

**Design Decisions:**
- **Singleton pattern:** Only initializes once per session (`csrfInitialized` flag)
- **Non-blocking:** Errors don't crash the app, actual API calls will fail with proper messages
- **Testable:** `resetCsrfState()` allows resetting for testing
- **Logging:** Console logs for debugging in development

#### 3. Frontend: API Client with CSRF Support

**File:** `web/src/features/auth/client.ts`

```typescript
// Get CSRF token from cookie
function getCsrfToken(): string | null {
  const name = 'csrftoken'
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null
  return null
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  
  // Add CSRF token for non-GET requests
  if (init.method && init.method !== 'GET') {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      headers.set('X-CSRFToken', csrfToken)
    } else {
      console.warn('⚠️ No CSRF token found! Check if /auth/csrf/ was called')
    }
  }
  
  const token = authStore.state.accessToken
  if (token) headers.set('Authorization', `Bearer ${token}`)
  
  const res = await fetch(`${API_BASE}${path}`, { 
    credentials: 'include', 
    ...init, 
    headers 
  })
  
  // ... error handling
}

export async function refreshAccessToken(): Promise<boolean> {
  const csrfToken = getCsrfToken()
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (csrfToken) headers['X-CSRFToken'] = csrfToken
  
  const res = await fetch(`${API_BASE}/auth/token/refresh/`, { 
    method: 'POST', 
    credentials: 'include',
    headers
  })
  // ... token handling
}
```

**Design Decisions:**
- **Cookie parsing:** Manual cookie parsing (no dependencies)
- **Automatic injection:** CSRF token added automatically to POST/PUT/PATCH/DELETE
- **Graceful degradation:** Warning logged if token missing, but request still sent
- **Credentials always included:** `credentials: 'include'` ensures cookies are sent/received

#### 4. Application Bootstrap

**File:** `web/src/main.tsx`

```typescript
import { ensureCsrfToken } from './lib/csrf.ts'
import { refreshAccessToken } from './features/auth/client.ts'

// Initialize app: fetch CSRF token first, then try to restore session
ensureCsrfToken().then(() => {
  return refreshAccessToken()
}).then(() => {
  root.render(
    <StrictMode>
      <TanStackQueryProvider.Provider>
        <RouterProvider router={router} />
      </TanStackQueryProvider.Provider>
    </StrictMode>,
  )
})
```

**Flow:**
1. App loads → Call `ensureCsrfToken()` to get CSRF cookie
2. Try `refreshAccessToken()` to restore session from refresh token cookie
3. Render application

**Rationale:**
- CSRF token must be available before any POST requests
- Token refresh happens early to restore sessions
- Sequential initialization ensures proper order

### Cookie Configuration

**Development (`mysite/settings_dev.py`):**

```python
# CSRF Settings
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-origin from localhost
CSRF_COOKIE_SECURE = False    # Allow HTTP (development only)
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

**Production (`mysite/settings_prod.py`):**

```python
# CSRF Settings
CSRF_COOKIE_HTTPONLY = False   # Allow JavaScript to read
CSRF_COOKIE_SAMESITE = 'Strict'  # Strict same-site policy
CSRF_COOKIE_SECURE = True      # HTTPS only
CSRF_TRUSTED_ORIGINS = [
    'https://tinybeans.com',
    'https://www.tinybeans.com',
]

# CORS Settings (if needed for subdomains)
CORS_ALLOWED_ORIGINS = [
    'https://tinybeans.com',
    'https://www.tinybeans.com',
]
CORS_ALLOW_CREDENTIALS = True
```

**Key Settings:**
- `CSRF_COOKIE_HTTPONLY = False`: **Critical** - Must be False so JavaScript can read the cookie
- `CORS_ALLOW_CREDENTIALS = True`: Required for cookies to work cross-origin
- `CSRF_TRUSTED_ORIGINS`: Must include all frontend origins
- `CSRF_COOKIE_SAMESITE`: 'Lax' for dev (cross-port), 'Strict' for production

### Authentication Flow with CSRF

#### Login Flow

```
┌────────┐                ┌──────────┐                ┌─────────┐
│ User   │                │ Frontend │                │ Backend │
└───┬────┘                └────┬─────┘                └────┬────┘
    │                          │                           │
    │   Visit login page       │                           │
    ├─────────────────────────>│                           │
    │                          │                           │
    │                          │  GET /auth/csrf/          │
    │                          ├──────────────────────────>│
    │                          │                           │
    │                          │  Set-Cookie: csrftoken    │
    │                          │<──────────────────────────┤
    │                          │                           │
    │   Enter credentials      │                           │
    ├─────────────────────────>│                           │
    │                          │                           │
    │                          │  POST /auth/login/        │
    │                          │  X-CSRFToken: abc123      │
    │                          │  Cookie: csrftoken=abc123 │
    │                          ├──────────────────────────>│
    │                          │                           │
    │                          │  200 OK + tokens          │
    │                          │<──────────────────────────┤
    │                          │                           │
    │   Logged in             │                           │
    │<─────────────────────────┤                           │
```

#### Token Refresh Flow

```
┌────────┐                ┌──────────┐                ┌─────────┐
│ User   │                │ Frontend │                │ Backend │
└───┬────┘                └────┬─────┘                └────┬────┘
    │                          │                           │
    │   Access expires         │                           │
    │                          │                           │
    │                          │  POST /auth/token/refresh/│
    │                          │  X-CSRFToken: abc123      │
    │                          │  Cookie: refresh_token    │
    │                          ├──────────────────────────>│
    │                          │                           │
    │                          │  200 OK + new access token│
    │                          │<──────────────────────────┤
    │                          │                           │
    │   Continue using app     │                           │
    │<─────────────────────────┤                           │
```

## Alternatives Considered

### Alternative 1: No CSRF Endpoint - Visit Root First

**Approach:** Frontend visits any Django page (e.g., `/api/`) to get CSRF cookie before login.

**Pros:**
- No dedicated endpoint needed
- Uses Django's automatic CSRF cookie setting

**Cons:**
- Implicit behavior - not obvious what's happening
- Might visit unnecessary endpoints
- Could load extra data (e.g., API root schema)
- Harder to debug when CSRF token missing

**Example:**
```typescript
// Visit API root to get CSRF cookie
await fetch(`${API_BASE}/`, { credentials: 'include' })
// Now csrftoken cookie is set
```

**Decision:** ❌ Rejected - Too implicit and potentially wasteful

### Alternative 2: Double-Submit Cookie Pattern (Manual)

**Approach:** Backend generates CSRF token and returns it in both cookie AND response body.

**Implementation:**
```python
# Backend
def login(request):
    csrf_token = get_token(request)
    return JsonResponse({
        'csrf_token': csrf_token,  # In response body
        # Also set in cookie automatically
    })
```

```typescript
// Frontend
const response = await fetch('/auth/login/', { credentials: 'include' })
const { csrf_token } = await response.json()
// Use csrf_token in subsequent requests
```

**Pros:**
- Token available immediately in response
- No extra endpoint needed
- Frontend can verify token matches cookie

**Cons:**
- Duplicates token in response body and cookie
- Every endpoint needs to return CSRF token
- Client needs to store token separately
- More complex client-side logic

**Decision:** ❌ Rejected - Unnecessary complexity, cookie-only approach is sufficient

### Alternative 3: Disable CSRF for API Endpoints

**Approach:** Use `@csrf_exempt` on all API views, rely on JWT auth only.

**Implementation:**
```python
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    # ...
```

**Pros:**
- Simplest implementation
- No CSRF token management needed
- Works seamlessly with JWT

**Cons:**
- ⚠️ **MAJOR SECURITY RISK** - Opens CSRF vulnerability
- Not following Django best practices
- Could allow attacks if JWT is stored in cookie
- Current implementation uses refresh token in httpOnly cookie (vulnerable to CSRF without token)

**When This Would Be Safe:**
- JWT stored ONLY in localStorage (never cookies)
- No session cookies used
- API completely stateless
- All authentication via Authorization header

**Current Situation:**
- ❌ Refresh token in httpOnly cookie → CSRF protection needed
- ✅ Access token in localStorage → Safe from CSRF
- **Result:** Cannot disable CSRF protection

**Decision:** ❌ Rejected - Security risk with current cookie-based refresh tokens

### Alternative 4: CSRF Token in LocalStorage

**Approach:** Store CSRF token in localStorage instead of reading from cookie.

**Implementation:**
```typescript
// After fetching CSRF token
const response = await fetch('/auth/csrf/')
const { csrf_token } = await response.json()
localStorage.setItem('csrf_token', csrf_token)

// In requests
const csrfToken = localStorage.getItem('csrf_token')
headers.set('X-CSRFToken', csrfToken)
```

**Pros:**
- Explicit token storage
- Easy to access
- No cookie parsing needed

**Cons:**
- Not Django's standard pattern
- Token must be returned in response body
- Client and server both manage token
- LocalStorage accessible to XSS attacks
- Cookie is already set by Django, this adds redundancy

**Decision:** ❌ Rejected - Redundant with cookie approach, doesn't provide benefits

### Alternative 5: Fetch CSRF Token on Every Login

**Approach:** Call `/auth/csrf/` immediately before login, not on app load.

**Implementation:**
```typescript
async function login(credentials) {
  // Get CSRF token
  await fetch('/auth/csrf/', { credentials: 'include' })
  
  // Now login
  return fetch('/auth/login/', {
    method: 'POST',
    body: JSON.stringify(credentials),
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCsrfToken()
    }
  })
}
```

**Pros:**
- Token fetched exactly when needed
- No app-wide initialization
- Works even if user sits on login page for hours

**Cons:**
- Extra request on every login (slower)
- Doesn't cover other POST endpoints (signup, password reset, etc.)
- CSRF token can expire while user is on the page
- App-wide initialization is more robust

**Decision:** ❌ Rejected - App-wide initialization is more reliable and covers all endpoints

### Alternative 6: Meta Tag in HTML (Traditional SSR)

**Approach:** Django renders initial HTML with CSRF token in meta tag.

**Implementation:**
```html
<!-- In Django template -->
<meta name="csrf-token" content="{{ csrf_token }}">
```

```typescript
// In frontend
const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
```

**Pros:**
- Traditional Django approach
- Token available immediately on page load
- No extra fetch request

**Cons:**
- Requires server-side rendering of frontend
- Doesn't work with SPA deployed separately
- Current architecture: frontend and backend are separate apps
- Token would be outdated if user stays on page long-term

**Decision:** ❌ Rejected - Incompatible with SPA architecture

## Consequences

### Positive

1. **Security**: Full CSRF protection for all state-changing operations
2. **Explicit**: Dedicated endpoint makes CSRF handling obvious and debuggable
3. **Performant**: Token fetched once per session, cached thereafter
4. **Standard**: Follows Django's recommended CSRF patterns
5. **Maintainable**: Simple, well-documented implementation
6. **Testable**: Can reset CSRF state for testing
7. **Automatic**: Once initialized, all POST requests include token automatically
8. **Development-friendly**: Works across different ports (localhost:3000 → 192.168.1.76:3053)

### Negative

1. **Extra Request**: One additional GET request on app load
2. **Cookie Dependency**: Requires cookies to be enabled
3. **CORS Configuration**: Needs proper CORS and CSRF trusted origins setup
4. **Browser Restrictions**: SameSite cookie policies can cause issues
5. **Debugging Complexity**: Cookie and header must match, can be confusing to debug
6. **HttpOnly = False**: CSRF cookie must be readable by JavaScript (less secure than HttpOnly=True)

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| CSRF token not initialized before POST | 403 Forbidden errors | App bootstrap calls `ensureCsrfToken()` before render |
| Cookie blocked by browser | Login fails | Warn user if cookies disabled, provide instructions |
| CORS misconfiguration | Cookie not set/sent | Comprehensive CORS settings documentation |
| Token expires during session | Subsequent requests fail | CSRF tokens don't expire (cookie is session-based) |
| Cookie not sent cross-origin | 403 on login | `credentials: 'include'` in all fetch calls |
| Development env cookie issues | Can't login locally | Document localhost/IP address configuration |
| Production SameSite=Strict too restrictive | Breaks external redirects | Use 'Lax' if needed, document trade-offs |

### Operational Considerations

**Monitoring:**
- Watch for 403 errors in logs (indicates CSRF failures)
- Track `/auth/csrf/` endpoint usage (should be ~once per user session)
- Monitor cookie set/read success rates

**Debugging:**
1. Check browser cookies: Look for `csrftoken` in DevTools
2. Check request headers: Look for `X-CSRFToken` in Network tab
3. Check console logs: Should see "CSRF token initialized"
4. Verify CORS settings: Check `Access-Control-Allow-*` headers

**Testing:**
```typescript
// Unit test example
import { ensureCsrfToken, resetCsrfState } from '@/lib/csrf'

beforeEach(() => {
  resetCsrfState()
})

test('fetches CSRF token once', async () => {
  const fetchSpy = jest.spyOn(global, 'fetch')
  await ensureCsrfToken()
  await ensureCsrfToken() // Second call
  expect(fetchSpy).toHaveBeenCalledTimes(1) // Only called once
})
```

## Future Enhancements

### 1. CSRF Token Rotation
**Description:** Rotate CSRF tokens periodically for additional security

**Implementation:**
```python
# After login, generate new CSRF token
from django.middleware.csrf import rotate_token
rotate_token(request)
```

**Pros:** Enhanced security against token leakage
**Cons:** Frontend must refetch token after certain operations

### 2. Device Fingerprinting with CSRF
**Description:** Bind CSRF token to device fingerprint

**Implementation:**
```python
# Store device fingerprint with CSRF token
# Validate both on requests
```

**Pros:** Prevent token theft/replay
**Cons:** Complex implementation, false positives

### 3. Content Security Policy (CSP) Headers
**Description:** Add CSP headers to further protect against XSS

**Implementation:**
```python
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
CSP_DEFAULT_SRC = ("'self'",)
```

**Pros:** Defense-in-depth security
**Cons:** Can break some third-party integrations

### 4. CSRF Token in Response Header
**Description:** Backend echoes CSRF token in response header

**Implementation:**
```python
# In middleware or view
response['X-CSRF-Token'] = get_token(request)
```

**Pros:** Frontend can verify token without cookie parsing
**Cons:** Redundant with cookie, more data transferred

## References

- [Django CSRF Protection Documentation](https://docs.djangoproject.com/en/stable/ref/csrf/)
- [OWASP Cross-Site Request Forgery (CSRF) Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [MDN: HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [SameSite Cookie Attribute Explained](https://web.dev/samesite-cookies-explained/)
- [Django REST Framework: CSRF](https://www.django-rest-framework.org/topics/ajax-csrf-cors/)

## Appendix A: Complete Code Examples

### Backend: Complete CSRF View

```python
# mysite/auth/views.py

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Endpoint to set CSRF cookie for the frontend.
    
    The @ensure_csrf_cookie decorator guarantees that the csrftoken
    cookie will be set on the response, even if the view doesn't
    otherwise require it.
    
    Usage:
        GET /api/auth/csrf/
        
    Returns:
        200 OK: {"detail": "CSRF cookie set"}
        
    Side Effects:
        Sets csrftoken cookie in response:
        Set-Cookie: csrftoken=<token>; Path=/; SameSite=Lax
    """
    return JsonResponse({'detail': 'CSRF cookie set'})
```

### Frontend: Complete CSRF Module

```typescript
// web/src/lib/csrf.ts

import { API_BASE } from '@/features/auth/client'

/**
 * Tracks whether CSRF token has been initialized.
 * Using module-level variable for singleton pattern.
 */
let csrfInitialized = false

/**
 * Initialize CSRF token by fetching from backend.
 * 
 * This function should be called once during app initialization,
 * before any POST/PUT/PATCH/DELETE requests are made.
 * 
 * The backend will set a csrftoken cookie in the response,
 * which will then be readable from document.cookie.
 * 
 * @returns Promise that resolves when CSRF token is initialized
 * 
 * @example
 * // In main.tsx
 * await ensureCsrfToken()
 * // Now all API requests will include CSRF token
 */
export async function ensureCsrfToken(): Promise<void> {
  // Skip if already initialized (idempotent)
  if (csrfInitialized) {
    console.log('CSRF token already initialized, skipping')
    return
  }

  try {
    const response = await fetch(`${API_BASE}/auth/csrf/`, {
      method: 'GET',
      credentials: 'include', // Required to receive cookies
    })
    
    if (!response.ok) {
      throw new Error(`CSRF endpoint returned ${response.status}`)
    }
    
    csrfInitialized = true
    console.log('✅ CSRF token initialized successfully')
  } catch (error) {
    console.error('❌ Failed to initialize CSRF token:', error)
    // Don't throw - let the actual API call fail with proper error
    // This prevents the app from crashing if CSRF endpoint is temporarily down
  }
}

/**
 * Reset CSRF initialization state.
 * 
 * Useful for:
 * - Testing: Reset state between tests
 * - Logout: Force re-initialization on next login
 * - Error recovery: Retry CSRF fetch after network errors
 * 
 * @example
 * // After logout
 * resetCsrfState()
 * // Next login will re-fetch CSRF token
 */
export function resetCsrfState(): void {
  csrfInitialized = false
  console.log('CSRF state reset')
}

/**
 * Check if CSRF has been initialized.
 * Useful for debugging and testing.
 * 
 * @returns boolean indicating if CSRF is initialized
 */
export function isCsrfInitialized(): boolean {
  return csrfInitialized
}
```

### Frontend: Complete API Client

```typescript
// web/src/features/auth/client.ts

import { authStore, setAccessToken } from './store'

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

/**
 * Extract CSRF token from document cookies.
 * 
 * Django sets the CSRF token in a cookie named 'csrftoken'.
 * This function parses document.cookie to extract that value.
 * 
 * @returns CSRF token string or null if not found
 * 
 * @example
 * const token = getCsrfToken()
 * if (token) {
 *   headers.set('X-CSRFToken', token)
 * }
 */
function getCsrfToken(): string | null {
  const name = 'csrftoken'
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  
  if (parts.length === 2) {
    const token = parts.pop()?.split(';').shift() || null
    return token
  }
  
  return null
}

/**
 * Make an HTTP request to the API with automatic CSRF and auth token injection.
 * 
 * Features:
 * - Automatically adds Content-Type: application/json for JSON payloads
 * - Automatically adds X-CSRFToken header for POST/PUT/PATCH/DELETE
 * - Automatically adds Authorization header if user is logged in
 * - Automatically includes credentials (cookies) in all requests
 * - Handles 401 errors by attempting token refresh
 * - Parses error responses into structured Error objects
 * 
 * @param path API endpoint path (e.g., '/auth/login/')
 * @param init Fetch API options
 * @returns Parsed JSON response
 * @throws Error with status and data properties on failure
 */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  
  // Set Content-Type for JSON payloads (skip for FormData)
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  
  // Add CSRF token for state-changing requests
  if (init.method && init.method !== 'GET') {
    const csrfToken = getCsrfToken()
    
    if (csrfToken) {
      headers.set('X-CSRFToken', csrfToken)
      console.log(`✅ Added CSRF token to ${init.method} ${path}`)
    } else {
      console.warn(`⚠️ No CSRF token found for ${init.method} ${path}`)
      console.warn('Check that ensureCsrfToken() was called during app initialization')
    }
  }
  
  // Add JWT access token if available
  const token = authStore.state.accessToken
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  
  // Make request with credentials to send/receive cookies
  const res = await fetch(`${API_BASE}${path}`, { 
    credentials: 'include', // Required for cookies
    ...init, 
    headers 
  })
  
  // Handle 401 Unauthorized with token refresh
  const skipRetry = path === '/auth/login/' || 
                    path === '/auth/signup/' || 
                    path === '/auth/token/refresh/'
  
  if (res.status === 401 && !skipRetry) {
    console.log('Received 401, attempting token refresh...')
    const refreshed = await refreshAccessToken()
    
    if (refreshed) {
      console.log('Token refreshed successfully, retrying request')
      return request<T>(path, init) // Retry with new token
    } else {
      console.log('Token refresh failed, user must log in again')
    }
  }
  
  // Handle errors
  if (!res.ok) {
    const data = await res.json().catch(() => ({} as any))
    const errorMessage = (data as any).detail || 
                        (data as any).message || 
                        res.statusText
    
    throw Object.assign(
      new Error(errorMessage), 
      {
        status: res.status,
        data,
      }
    )
  }
  
  return res.json()
}

/**
 * Refresh the JWT access token using the refresh token cookie.
 * 
 * The refresh token is stored in an httpOnly cookie named 'refresh_token'.
 * This function sends a POST request to /auth/token/refresh/ with the
 * CSRF token to get a new access token.
 * 
 * @returns Promise<boolean> true if refresh successful, false otherwise
 */
export async function refreshAccessToken(): Promise<boolean> {
  const csrfToken = getCsrfToken()
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken
  } else {
    console.warn('⚠️ No CSRF token available for token refresh')
  }
  
  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, { 
      method: 'POST', 
      credentials: 'include', // Send refresh_token cookie
      headers
    })
    
    if (!res.ok) {
      console.log('Token refresh failed:', res.status, res.statusText)
      return false
    }
    
    const data = await res.json().catch(() => null) as any
    
    if (data?.access) {
      setAccessToken(data.access)
      console.log('✅ Access token refreshed successfully')
      return true
    }
    
    console.log('Token refresh response missing access token')
    return false
  } catch (error) {
    console.error('Token refresh error:', error)
    return false
  }
}

/**
 * API client with common HTTP methods.
 * All methods automatically handle CSRF tokens and authentication.
 */
export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: any) => request<T>(path, { 
    method: 'POST', 
    body: body ? JSON.stringify(body) : undefined 
  }),
  patch: <T>(path: string, body?: any) => request<T>(path, { 
    method: 'PATCH', 
    body: body ? JSON.stringify(body) : undefined 
  }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  put: <T>(path: string, body?: any) => request<T>(path, { 
    method: 'PUT', 
    body: body ? JSON.stringify(body) : undefined 
  }),
}
```

## Appendix B: Troubleshooting Guide

### Problem: 403 Forbidden on Login

**Symptoms:**
```
POST /api/auth/login/ 403 (Forbidden)
{"detail": "CSRF Failed: CSRF token missing or incorrect."}
```

**Diagnosis Steps:**

1. **Check if CSRF cookie exists:**
```javascript
// In browser console
document.cookie.split(';').find(c => c.includes('csrftoken'))
```
Should return: `" csrftoken=abc123..."`

2. **Check if X-CSRFToken header is sent:**
Open DevTools → Network → Click the failed request → Headers
Look for: `X-CSRFToken: abc123...`

3. **Check if cookie matches header:**
The cookie value and header value must match exactly.

**Solutions:**

| Issue | Solution |
|-------|----------|
| Cookie not set | Call `ensureCsrfToken()` before login |
| Cookie set but header missing | Check `getCsrfToken()` function |
| Cookie and header don't match | Clear cookies and reload page |
| Cookie blocked by browser | Check cookie settings, enable third-party cookies for dev |

### Problem: CORS Error Before 403

**Symptoms:**
```
Access to fetch at 'http://192.168.1.76:3053/api/auth/login/' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solution:**

Check Django settings:
```python
# Must have BOTH frontend origins
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://192.168.1.76:3053',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://192.168.1.76:3053',
]

# Critical!
CORS_ALLOW_CREDENTIALS = True
```

### Problem: Cookie Not Sent in Request

**Symptoms:**
- Cookie visible in Application tab
- Cookie NOT in Network request headers

**Diagnosis:**
```javascript
// Check SameSite policy
document.cookie
```

**Solutions:**

1. **Development (cross-origin):**
```python
CSRF_COOKIE_SAMESITE = 'Lax'  # Not 'Strict'
CSRF_COOKIE_SECURE = False    # Not True (for HTTP)
```

2. **Ensure credentials in fetch:**
```typescript
fetch(url, { credentials: 'include' }) // Required!
```

### Problem: CSRF Token Expires

**Symptoms:**
- Login works initially
- After some time, requests fail with 403

**Note:** Django CSRF tokens are session-based and don't expire unless:
- User logs out
- Session expires
- Cookies cleared

**Solution:**
```typescript
// Call ensureCsrfToken() again after logout
export function useLogout() {
  return useMutation({
    mutationFn: async () => {
      await api.post('/auth/logout/')
      setAccessToken(null)
      resetCsrfState() // Force re-fetch on next login
    }
  })
}
```

---

**Date:** 2025-01-08  
**Author:** Development Team  
**Status:** Implemented and Tested  
**Last Updated:** 2025-01-08
