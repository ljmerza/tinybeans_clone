# Email Verification Flow Redesign - Planning Document

## Executive Summary

This document outlines the plan to redesign the email verification flow to make email verification **mandatory before onboarding**, rather than optional during onboarding.

### What's Changing - Visual Summary

#### ❌ REMOVING (Old Flow)
```
User signs up
   ↓
Goes directly to onboarding
   ↓
Onboarding shows:
  ✉️ Email verification UI (resend/refresh buttons)
  ⏭️ Can skip verification
   ↓
Settings page shows:
  ✉️ Verification status badges
  🔄 Resend/refresh buttons
   ↓
Verify link → Shows success page → Manual redirect
```

#### ✅ ADDING (New Flow)
```
User signs up (email/password)
   ↓
Redirected to /verify-email-required (BLOCKING PAGE)
   ✉️ "Check your email" message
   🔄 Resend button (if needed)
   ↓
Click email link
   ↓
Backend: Auto-login (JWT tokens + cookie)
   ↓
Redirect to onboarding + toast notification
   ↓
Onboarding: Clean UI, no verification controls
   ↓
Settings: Clean UI, email display only

SPECIAL: OAuth users skip verification entirely
```

---

## Current Flow Issues

1. **Email verification is optional**: Users can skip email verification and access the app
2. **Verification UI in multiple places**: Email verification controls appear in both onboarding and settings
3. **Confusing user journey**: Users can access onboarding immediately after signup without verifying email
4. **Inconsistent experience**: Verification link redirects to a dedicated verify page, not onboarding

---

## Desired Flow

### User Journey
```
1. User creates account at /signup
   ↓
2. User redirected to /verify-email-required page
   - Shows message: "Please verify your email to continue"
   - Shows their email address
   - Option to resend verification email
   - Cannot access onboarding or app features
   ↓
3. User receives email with verification link
   ↓
4. User clicks verification link
   ↓
5. Backend verifies token + sets email_verified = true
   ↓
6. User redirected to /circles/onboarding (NOT /verify-email)
   - Toast notification: "Email verified successfully!"
   - Onboarding form shows immediately (no verification UI)
   - Can create circle or skip
   ↓
7. User completes/skips onboarding → enters app
```

### Key Changes
- ✅ Email verification is **mandatory** before accessing onboarding
- ✅ Verification link redirects to **onboarding** (not verify page)
- ✅ **Auto-login** via verification link (secure magic link authentication)
- ✅ Toast notification on successful verification
- ✅ **OAuth users skip** email verification (Google OAuth pre-verified)
- ✅ **Remove** email verification UI from onboarding page
- ✅ **Remove** email verification UI from settings page
- ✅ Onboarding only accessible after email verification
- ✅ **Resend rate limits preserved** (5 per 15 min per IP/identifier)

---

## Technical Implementation Plan

### Phase 1: Backend Changes

#### 1.1 Create Email Verification Service Layer (NEW)
**New File**: `mysite/auth/services/email_verification.py`

**Purpose**: Separate business logic from views for better architecture and testability

**Implementation**:
```python
"""Email verification service layer"""
import logging
from typing import Tuple
from django.db import transaction
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Service for email verification operations"""

    @transaction.atomic
    def verify_and_login(self, user) -> Tuple[str, str]:
        """
        Verify user email and generate fresh auth tokens.

        Args:
            user: User instance to verify

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            ValueError: If user is inactive or verification fails
        """
        # Validation: User must be active
        if not user.is_active:
            raise ValueError("Cannot verify inactive user account")

        # Log re-verification attempts (could indicate token reuse)
        if user.email_verified:
            logger.warning(
                f"Re-verification attempt for already verified user {user.id}",
                extra={"user_id": user.id}
            )

        # Update user email_verified flag
        user.email_verified = True
        user.save(update_fields=["email_verified"])

        # Generate fresh JWT tokens for auto-login
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return access_token, refresh_token
```

#### 1.2 Update Email Verification Confirm View (Add Auto-Login)
**File**: `mysite/auth/views.py` (lines 479-553)

**Changes**:
- Use service layer for business logic (transaction-safe)
- Generate fresh JWT tokens via EmailVerificationService
- Return tokens + redirect URL + safe user data
- Set secure HTTP-only refresh cookie
- Add comprehensive error handling
- Log audit event with IP/user agent

**Security Measures**:
- ✅ Token single-use via `pop_token()` (existing)
- ✅ Token time-limited with TTL (existing)
- ✅ Rate limiting: 5 per 15 min per IP/identifier (existing)
- ✅ Transaction-wrapped verification + token generation (new)
- ✅ User active status validation (new)
- ✅ Generate fresh JWT tokens (new)
- ✅ Secure HTTP-only refresh cookie with domain/path (new)
- ✅ Safe user serializer (PublicUserSerializer) (new)
- ✅ Comprehensive error handling (new)
- ✅ Centralized cookie configuration (new)
- ✅ Audit logging with IP/device info (enhanced)

**Implementation**:
```python
# In EmailVerificationConfirmView.post()
import logging
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from .services.email_verification import EmailVerificationService
from ..users.serializers import PublicUserSerializer
from ..audit.models import AuditLog

logger = logging.getLogger(__name__)


def post(self, request):
    """
    Verify email token and auto-login user.

    Returns JWT tokens and redirects to onboarding.
    """
    # Validate verification token
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data["user"]

    try:
        # Use service layer for verification + token generation
        service = EmailVerificationService()
        access_token, refresh_token = service.verify_and_login(user)

        # Build response with tokens and safe user data
        response = Response(
            {
                "message": "Email verified successfully.",
                "redirect_url": "/circles/onboarding",
                "access_token": access_token,
                "user": PublicUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

        # Set refresh token cookie using environment-aware settings
        cookie_kwargs = {
            "key": "refresh_token",
            "value": refresh_token,
            "max_age": 60 * 60 * 24 * 7,  # 7 days
            "httponly": True,  # Not accessible via JavaScript
            "secure": getattr(settings, "SESSION_COOKIE_SECURE", True),
            "samesite": getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
            "path": "/",  # Available to entire app
        }
        domain = getattr(settings, "SESSION_COOKIE_DOMAIN", None)
        if domain:
            cookie_kwargs["domain"] = domain
        response.set_cookie(**cookie_kwargs)

        # Audit logging
        AuditLog.objects.create(
            user=user,
            action="email_verified_with_auto_login",
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"auto_login": True},
        )

        logger.info(f"Email verified and auto-login for user {user.id}")

        return response

    except ValueError as e:
        # User validation errors (inactive user, etc.)
        logger.warning(f"Email verification validation failed: {e}")
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        # Unexpected errors (token generation, database, etc.)
        logger.error(
            f"Email verification failed for user {user.id}: {e}",
            exc_info=True
        )
        return Response(
            {"detail": "Email verification failed. Please try again or contact support."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

def _get_client_ip(self, request):
    """Get client IP from request, handling proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

#### 1.3 Create Email Verification Permission Class (NEW)
**New File**: `mysite/auth/permissions.py`

**Purpose**: Reusable DRF permission for email-verified requirement (DRY, testable, applies to all HTTP methods)

**Implementation**:
```python
"""Custom DRF permissions for authentication"""
from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    """
    Permission that requires authenticated user with verified email.

    Returns 403 with specific error code that frontend intercepts
    and redirects to /verify-email-required.

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsEmailVerified]
    """

    message = {
        'error': 'email_verification_required',
        'detail': 'Email verification required to access this resource.',
        'redirect_to': '/verify-email-required'
    }

    def has_permission(self, request, view):
        """Check if user is authenticated, active, and email verified"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        if not getattr(request.user, 'email_verified', False):
            # DRF automatically serializes self.message into the 403 response
            return False

        return True
```

#### 1.4 Update Onboarding View with Permission Class
**File**: `mysite/users/views/onboarding.py`

**Changes**:
- Add `IsEmailVerified` permission class (applies to ALL methods: GET, POST, PUT, etc.)
- Remove inline permission checks (cleaner architecture)
- Permission automatically returns 403 with clear message

**Implementation**:
```python
from rest_framework.permissions import IsAuthenticated
from mysite.auth.permissions import IsEmailVerified


class CircleOnboardingView(APIView):
    """
    Circle onboarding endpoint.

    Requires authenticated user with verified email.
    """
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request):
        """Get onboarding status"""
        # Permission already enforced by DRF - no inline checks needed
        # ... existing onboarding logic ...
        pass

    def post(self, request):
        """Create circle during onboarding"""
        # Also protected automatically by permission_classes
        # ... existing circle creation logic ...
        pass
```

**Architecture Benefits**:
- ✅ DRY: Reusable across all views requiring email verification
- ✅ Secure: Protects ALL HTTP methods (GET, POST, PUT, DELETE, etc.)
- ✅ Testable: Permission logic isolated and easily unit tested
- ✅ Consistent: Same error message across entire API
- ✅ Declarative: Clear intent via permission_classes declaration

#### 1.4.1 Apply Email Verification to ALL API Endpoints (CRITICAL)
**Purpose**: Ensure unverified users can ONLY access auth endpoints and verification endpoints

**Problem**: If we only protect onboarding API, unverified users can access other APIs

**Solution Options**:

**Option A: Add to Every Protected View (Explicit)**
```python
# Apply to EVERY authenticated API view

# mysite/circles/views.py
class CircleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]  # ADD IsEmailVerified

# mysite/users/views/profile.py
class ProfileView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]  # ADD IsEmailVerified

# Repeat for ALL authenticated views
```

**Option B: Global Default Permission Classes with Custom Error Response (Recommended - DRY)**
```python
# mysite/config/settings/base.py

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'mysite.auth.permissions.IsEmailVerified',  # ADD THIS GLOBALLY
    ],
    # ... other settings ...
}
```

**Update Permission Class to Return Redirect Info**:
```python
# mysite/auth/permissions.py

class IsEmailVerified(BasePermission):
    """
    Permission that requires authenticated user with verified email.

    Returns 403 with specific error code that frontend can intercept
    and redirect to /verify-email-required.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated, active, and email verified"""
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_active:
            return False

        # Check email verification
        if not getattr(request.user, 'email_verified', False):
            # Permission denied - frontend should redirect
            # We set a custom message that frontend can recognize
            self.message = {
                'error': 'email_verification_required',
                'detail': 'Email verification required to access this resource.',
                'redirect_to': '/verify-email-required'
            }
            return False

        return True
```

**Then exempt specific views that don't need email verification**:
```python
# mysite/auth/views.py - Views that should work WITHOUT email verification

class LoginView(APIView):
    permission_classes = [AllowAny]  # Override global - no auth needed

class SignupView(APIView):
    permission_classes = [AllowAny]  # Override global - no auth needed

class EmailVerificationConfirmView(APIView):
    permission_classes = [AllowAny]  # Override global - verification endpoint itself

class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]  # Override global - only auth, not verified

    # This endpoint MUST be accessible to unverified users
    # so they can request verification emails
```

**Option C: Custom Middleware (Alternative)**
```python
# mysite/auth/middleware.py

class EmailVerificationMiddleware:
    """Middleware to enforce email verification globally."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt paths that don't need email verification
        exempt_paths = [
            '/api/auth/login/',
            '/api/auth/signup/',
            '/api/auth/verify-email/',
            '/api/auth/resend-verification/',
            '/api/auth/google/',
        ]

        is_exempt = any(request.path.startswith(path) for path in exempt_paths)

        if not is_exempt and request.user.is_authenticated:
            if not getattr(request.user, 'email_verified', False):
                return JsonResponse(
                    {
                        'error': 'email_verification_required',
                        'detail': 'Email verification required to access this resource.',
                    },
                    status=403
                )

        return self.get_response(request)
```

**Recommended Approach**: **Option B (Global Default Permission Classes)**

**Why**:
- ✅ DRY - Single configuration
- ✅ Comprehensive - Automatically protects all API views
- ✅ Explicit - Clear override for endpoints that shouldn't require verification
- ✅ Django REST Framework native - Works with existing permission system
- ✅ Testable - Can test permission class in isolation

**API Endpoints That Should NOT Require Email Verification**:
```python
exempt_views = [
    # Auth endpoints
    'LoginView',
    'SignupView',
    'LogoutView',
    'RefreshTokenView',

    # Email verification endpoints (must work for unverified users)
    'EmailVerificationConfirmView',
    'ResendVerificationEmailView',

    # OAuth endpoints
    'GoogleOAuthInitiateView',
    'GoogleOAuthCallbackView',

    # Password reset endpoints
    'ForgotPasswordView',
    'ResetPasswordView',
]
```

**Implementation**:
```python
# mysite/config/settings/base.py

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'mysite.auth.permissions.IsEmailVerified',  # Global email verification
    ],
    # ... other settings
}
```

```python
# mysite/auth/views.py

class ResendVerificationEmailView(APIView):
    """
    Resend email verification.

    IMPORTANT: Must override global permission to allow unverified users.
    """
    permission_classes = [IsAuthenticated]  # Only auth, not IsEmailVerified

    def post(self, request):
        # Unverified users can request verification emails
        # ...
```

**Testing**:
- [ ] Test unverified user gets redirected (not 403 error) when accessing `/api/circles/`
- [ ] Test unverified user gets redirected when accessing `/api/users/profile/`
- [ ] Test unverified user CAN access `/api/auth/resend-verification/`
- [ ] Test unverified user CAN access `/api/auth/verify-email/`
- [ ] Test verified user CAN access all protected endpoints
- [ ] Test API interceptor catches `email_verification_required` error and redirects
- [ ] Test toast message appears when redirected from API error

#### 1.5 OAuth User Auto-Verification ✅ ALREADY IMPLEMENTED
**Files**:
- `mysite/auth/services/google_oauth_service.py` (lines 311-407)
- `mysite/auth/views_google_oauth.py` (lines 134-275)

**Status**: ✅ **NO CHANGES NEEDED** - Google OAuth already sets `email_verified=True`

**Current Implementation Analysis**:

**Location 1: New Google User Creation** (line 391):
```python
# mysite/auth/services/google_oauth_service.py
@transaction.atomic
def get_or_create_user(self, google_user_info: Dict[str, any]) -> Tuple[User, str]:
    # ... (scenario checks) ...

    # Create new Google-only user
    new_user = User.objects.create(
        username=username,
        email=google_email,
        google_id=google_id,
        google_email=google_email,
        first_name=google_user_info.get('given_name', ''),
        last_name=google_user_info.get('family_name', ''),
        email_verified=True,  # ✅ ALREADY SET - Google verifies emails
        auth_provider='google',
        password_login_enabled=False,
        google_linked_at=timezone.now(),
        last_google_sync=timezone.now()
    )
    # ...
    return new_user, 'created'
```

**Location 2: Linking Google to Existing Verified Account** (line 368):
```python
# When email exists with verified account
existing_user.google_id = google_id
existing_user.google_email = google_email
existing_user.auth_provider = 'hybrid'
existing_user.google_linked_at = timezone.now()
existing_user.last_google_sync = timezone.now()
existing_user.email_verified = True  # ✅ ALREADY ENSURED
existing_user.save()
```

**Location 3: Manual Google Account Linking** (line 471):
```python
# mysite/auth/services/google_oauth_service.py
def link_google_account(self, user: User, google_user_info: Dict[str, any]) -> User:
    # ... validation ...
    user.google_id = google_id
    user.google_email = google_email
    user.auth_provider = 'hybrid' if user.password_login_enabled else 'google'
    user.google_linked_at = timezone.now()
    user.last_google_sync = timezone.now()
    user.email_verified = True  # ✅ ALREADY SET
    user.save()
```

**Security Implementation Details**:
- ✅ **Custom Implementation**: Not using python-social-auth or django-allauth
- ✅ **PKCE Flow**: Uses code_verifier/code_challenge for security
- ✅ **State Token Validation**: Prevents CSRF attacks
- ✅ **Nonce Verification**: Prevents replay attacks
- ✅ **ID Token Verification**: Validates Google's signature
- ✅ **Transaction Safety**: All user creation wrapped in `@transaction.atomic`
- ✅ **Unverified Account Block**: Prevents account takeover (line 355-360)
- ✅ **Audit Logging**: OAuth events logged with IP/user agent

**What This Means for Our Implementation**:
- ✅ **No Code Changes Needed**: Email verification already handled correctly
- ✅ **Existing Users Work**: OAuth users can already skip email verification
- ✅ **Security Already Strong**: Unverified account takeover prevention in place
- ✅ **Testing Required**: Verify OAuth flow works with new verification-required page

**Testing Checklist**:
- [ ] Test Google OAuth signup → verify `email_verified=True` set
- [ ] Test Google OAuth signup → verify redirects to onboarding (not /verify-email-required)
- [ ] Test linking Google to existing verified account → works correctly
- [ ] Test OAuth with unverified manual account → verify blocked (security)
- [ ] Verify frontend signup logic handles `email_verified=true` for OAuth users

#### 1.6 Create PublicUserSerializer (NEW)
**New File**: `mysite/users/serializers.py` (or update existing)

**Purpose**: Safe user serializer that only exposes necessary fields (prevents data leakage)

**Implementation**:
```python
"""User serializers"""
from rest_framework import serializers
from .models import User


class PublicUserSerializer(serializers.ModelSerializer):
    """
    Safe user serializer for public API responses.

    Only exposes non-sensitive user information.
    Use this instead of full UserSerializer for API responses.
    """

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'email_verified',
            'first_name',
            'last_name',
            'needs_circle_onboarding',
            'circle_onboarding_status',
        ]
        read_only_fields = fields  # All fields read-only for safety


# Note: Explicitly EXCLUDE sensitive fields:
# - password, last_login, is_staff, is_superuser
# - date_joined, groups, user_permissions
```

#### 1.7 Update Signup Response (REQUIRED)
**File**: `mysite/auth/views.py` (lines 69-142)

**Changes** (REQUIRED, not optional):
- Add `email_verified` field to signup response
- Frontend uses this to determine redirect destination
- Use PublicUserSerializer for safe user data

**Implementation**:
```python
# In SignupView.post() response

from ..users.serializers import PublicUserSerializer

# After user creation
response_data = {
    "message": "Account created successfully.",
    "user": PublicUserSerializer(user).data,  # Includes email_verified
    "access_token": access_token,
    # ... other fields ...
}

# Note: email_verified will be False for email/password signups
# and True for OAuth signups (handled in OAuth callback)
```

**Why This Is Required**:
- Frontend needs `email_verified` to route correctly
- OAuth users should go to onboarding immediately
- Email/password users should go to verification page
- Without this, frontend can't distinguish signup types

---

### Phase 2: Frontend Routing Changes

#### 2.1 Create New Route: Verify Email Required
**New File**: `web/src/routes/verify-email-required.tsx`

**Purpose**: Blocking page shown after signup until email is verified

**Route**: `/verify-email-required`

**Guards**:
- `requireAuth` - Only authenticated users
- `requireEmailUnverified` - Redirect verified users to onboarding (prevent manual navigation)

**Component Features**:
- Display message: "Check your email to verify your account"
- Show user's email address from session
- "Resend verification email" button with rate limiting feedback
- Link to logout
- NO polling - verification link will auto-login and redirect

**Implementation**:
```typescript
// web/src/routes/verify-email-required.tsx
import { createFileRoute, redirect } from '@tanstack/react-router';
import { requireAuth } from '@/features/auth/guards/requireAuth';

export const Route = createFileRoute("/verify-email-required")({
  beforeLoad: ({ context }) => {
    // Guard 1: Must be authenticated
    requireAuth(context);

    // Guard 2: If already verified, redirect to onboarding
    if (context.auth.user?.email_verified) {
      throw redirect({ to: "/circles/onboarding" });
    }
  },
  component: VerifyEmailRequiredRoute,
});

function VerifyEmailRequiredRoute() {
  const { user } = useAuthSession();
  const resendMutation = useResendVerificationEmail();

  const handleResend = () => {
    resendMutation.mutate(user?.email, {
      onSuccess: () => {
        toast.success("Verification email sent! Check your inbox.");
      },
      onError: (error) => {
        const message = error.response?.data?.detail || "Failed to resend email";
        toast.error(message);
      },
    });
  };

  if (!user) return null;  // Should never happen due to requireAuth

  return (
    <div>
      <h1>Verify Your Email</h1>
      <p>We sent a verification email to <strong>{user.email}</strong></p>
      <p>Click the link in the email to continue to your account</p>

      <button
        onClick={handleResend}
        disabled={resendMutation.isPending}
      >
        {resendMutation.isPending ? "Sending..." : "Resend verification email"}
      </button>

      <a href="/logout">Logout</a>
    </div>
  );
}
```

**Architecture Benefits**:
- ✅ Prevents verified users from accessing (guard redirect)
- ✅ No polling - verification link handles auto-login and redirect directly
- ✅ Uses session directly (not circle onboarding hook)
- ✅ Proper error handling for resend
- ✅ Rate limit errors shown to user
- ✅ No DoS risk from continuous polling

#### 2.2 Update Signup Flow
**File**: `web/src/features/auth/components/SignupCard.tsx`

**Changes**:
- After successful signup, check `email_verified` status
- Email/password users → redirect to `/verify-email-required`
- OAuth users (pre-verified) → redirect to onboarding
- Add defensive error handling
- Update auth context with new user data

**Implementation**:
```typescript
// In SignupCard component

const signupMutation = useSignup({
  onSuccess: async (response) => {
    try {
      // Defensive: Ensure response has expected structure
      if (!response?.user) {
        throw new Error("Invalid signup response: missing user data");
      }

      // Update auth context with new user
      auth.setUser(response.user);
      auth.setAccessToken(response.access_token);

      // Route based on email verification status
      const { email_verified, needs_circle_onboarding } = response.user;

      if (!email_verified) {
        // Email/password signup: Must verify email first
        navigate({ to: "/verify-email-required" });
      } else if (needs_circle_onboarding) {
        // OAuth signup (pre-verified): Go to onboarding
        navigate({ to: "/circles/onboarding" });
      } else {
        // Already onboarded (edge case): Go to app
        navigate({ to: "/" });
      }
    } catch (error) {
      console.error("Signup navigation error:", error);
      toast.error("Signup successful, but navigation failed. Please refresh the page.");
    }
  },
  onError: (error) => {
    const message = error.response?.data?.detail || "Signup failed. Please try again.";
    toast.error(message);
  },
});
```

**Error Handling**:
- ✅ Validates response structure
- ✅ Handles missing data gracefully
- ✅ Logs errors for debugging
- ✅ Shows user-friendly error messages
- ✅ Updates auth context before navigation

#### 2.3 Update Email Verification Handler (Auto-Login Support)
**File**: `web/src/features/auth/components/EmailVerificationHandler.tsx`

**Changes**:
- Handle auto-login tokens from backend response
- Store access token and update user in auth context
- Backend sets refresh token cookie automatically (HTTP-only)
- Show toast notification after successful verification
- Redirect to onboarding (use backend redirect_url)
- Comprehensive error handling

**Implementation**:
```typescript
// EmailVerificationHandler.tsx

import { useEffect } from 'react';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { useVerifyEmailConfirm } from '@/features/auth/hooks/useVerifyEmailConfirm';
import { useAuth } from '@/features/auth/context/AuthContext';
import { toast } from 'sonner';

export function EmailVerificationHandler() {
  const navigate = useNavigate();
  const { token } = useSearch({ from: '/verify-email' });  // Get token from URL
  const { setAccessToken, setUser } = useAuth();

  const verifyMutation = useVerifyEmailConfirm({
    onSuccess: (response) => {
      try {
        // Validate response structure
        if (!response?.access_token || !response?.user) {
          throw new Error("Invalid verification response");
        }

        // Update auth context with auto-login tokens
        setAccessToken(response.access_token);
        setUser(response.user);  // User now has email_verified: true

        // Show success notification
        toast.success("Email verified successfully!");

        // Navigate to redirect URL (default: onboarding)
        const redirectUrl = response.redirect_url || "/circles/onboarding";
        navigate({ to: redirectUrl });

      } catch (error) {
        console.error("Verification success handler error:", error);
        toast.error("Verification succeeded but login failed. Please log in manually.");
        navigate({ to: "/login" });
      }
    },
    onError: (error) => {
      const message = error.response?.data?.detail || "Email verification failed";
      toast.error(message);

      // Redirect to login on error
      navigate({ to: "/login" });
    },
  });

  // Auto-verify when component mounts with token
  useEffect(() => {
    if (token && !verifyMutation.isPending) {
      verifyMutation.mutate(token);
    }
  }, [token]);

  return (
    <div>
      {verifyMutation.isPending && <p>Verifying your email...</p>}
      {verifyMutation.isError && <p>Verification failed. Redirecting...</p>}
    </div>
  );
}
```

**Hook Update** (`web/src/features/auth/hooks/useVerifyEmailConfirm.ts`):
```typescript
import { useMutation } from '@tanstack/react-query';
import { authService } from '@/features/auth/services/authService';

interface VerifyEmailConfirmResponse {
  message: string;
  redirect_url: string;
  access_token: string;
  user: {
    id: number;
    username: string;
    email: string;
    email_verified: boolean;
    needs_circle_onboarding: boolean;
    // ... other user fields
  };
}

interface UseVerifyEmailConfirmOptions {
  onSuccess?: (data: VerifyEmailConfirmResponse) => void;
  onError?: (error: any) => void;
}

export function useVerifyEmailConfirm(options?: UseVerifyEmailConfirmOptions) {
  return useMutation({
    mutationFn: async (token: string) => {
      const response = await authService.verifyEmailConfirm({ token });
      return response as VerifyEmailConfirmResponse;
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}
```

**Architecture Benefits**:
- ✅ Proper hook composition (options pattern)
- ✅ Comprehensive error handling
- ✅ Response validation before auth update
- ✅ Graceful degradation (redirect to login on error)
- ✅ User-friendly error messages
- ✅ TypeScript types for response
- ✅ Auto-login tokens properly stored

#### 2.4 Create Email Verification Guard (Reusable)
**New File**: `web/src/features/auth/guards/requireEmailVerified.ts`

**Purpose**: Reusable guard for routes requiring verified email (DRY, testable, consistent)

**Implementation**:
```typescript
// web/src/features/auth/guards/requireEmailVerified.ts

import { redirect } from '@tanstack/react-router';
import type { RouterContext } from '@/lib/router';

/**
 * Guard that requires user to have verified email.
 *
 * Redirects to /verify-email-required if email not verified.
 * Use after requireAuth guard.
 *
 * @param context - Router context with auth state
 * @throws Redirect to /verify-email-required if email not verified
 */
export function requireEmailVerified(context: RouterContext) {
  const user = context.auth.user;

  // User must exist (requireAuth should run first)
  if (!user) {
    throw redirect({ to: "/login" });
  }

  // User must have verified email
  if (!user.email_verified) {
    throw redirect({ to: "/verify-email-required" });
  }
}
```

#### 2.5 Update Onboarding Route with Guards
**File**: `web/src/routes/circles/onboarding.tsx`

**Changes**:
- Import and use `requireEmailVerified` guard
- Proper guard ordering (auth → email → onboarding status)
- Keep existing `requireCircleOnboardingIncomplete` guard

**Implementation**:
```typescript
// web/src/routes/circles/onboarding.tsx

import { createFileRoute } from '@tanstack/react-router';
import { requireAuth } from '@/features/auth/guards/requireAuth';
import { requireEmailVerified } from '@/features/auth/guards/requireEmailVerified';
import { requireCircleOnboardingIncomplete } from '@/features/circles/guards/requireCircleOnboardingIncomplete';

export const Route = createFileRoute("/circles/onboarding")({
  beforeLoad: ({ context }) => {
    // Guard 1: Must be authenticated
    requireAuth(context);

    // Guard 2: Must have verified email
    requireEmailVerified(context);

    // Guard 3: Must not have completed onboarding yet
    requireCircleOnboardingIncomplete(context);
  },
  component: CircleOnboardingRoute,
});

function CircleOnboardingRoute() {
  // ... onboarding component implementation
}
```

**Guard Ordering Rationale**:
1. **requireAuth**: Check authentication first (cheapest check)
2. **requireEmailVerified**: Check email verification (prerequisite for onboarding)
3. **requireCircleOnboardingIncomplete**: Check onboarding status (most specific)

**Architecture Benefits**:
- ✅ Guards in separate files (reusable across routes)
- ✅ Clear ordering and dependencies
- ✅ Each guard has single responsibility
- ✅ Guards are testable in isolation
- ✅ Consistent error/redirect behavior
- ✅ Self-documenting code with comments

#### 2.6 Apply Email Verification to ALL Protected Routes (CRITICAL)
**Purpose**: Ensure unverified users can ONLY access verification page and public routes

**Problem**: If we only protect onboarding, unverified users can access other app pages

**Solution**: Apply `requireEmailVerified` guard globally to all authenticated routes

**Option A: Route-by-Route (Explicit)**
```typescript
// Apply to EVERY protected route individually

// web/src/routes/circles/$circleId.tsx
export const Route = createFileRoute("/circles/$circleId")({
  beforeLoad: ({ context }) => {
    requireAuth(context);
    requireEmailVerified(context); // ADD THIS
  },
});

// web/src/routes/settings.tsx
export const Route = createFileRoute("/settings")({
  beforeLoad: ({ context }) => {
    requireAuth(context);
    requireEmailVerified(context); // ADD THIS
  },
});

// Repeat for ALL authenticated routes
```

**Option B: Root Layout Guard (Recommended - DRY)**
```typescript
// web/src/routes/_authenticated.tsx (or similar layout route)

import { createFileRoute, Outlet, redirect } from '@tanstack/react-router';
import { requireAuth } from '@/features/auth/guards/requireAuth';

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: ({ context, location }) => {
    // Check authentication
    requireAuth(context);

    // Check email verification (except for allowed routes)
    const allowedUnverifiedRoutes = [
      '/verify-email-required',
      '/logout',
    ];

    const isAllowedRoute = allowedUnverifiedRoutes.some(route =>
      location.pathname.startsWith(route)
    );

    if (!isAllowedRoute && !context.auth.user?.email_verified) {
      throw redirect({ to: "/verify-email-required" });
    }
  },
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  return <Outlet />;
}
```

**Then nest all protected routes under `_authenticated`**:
```typescript
// web/src/routes/_authenticated/circles/$circleId.tsx
export const Route = createFileRoute("/_authenticated/circles/$circleId")({
  // Email verification already checked by parent layout
  component: CircleDetailRoute,
});

// web/src/routes/_authenticated/settings.tsx
export const Route = createFileRoute("/_authenticated/settings")({
  // Email verification already checked by parent layout
  component: SettingsRoute,
});
```

**Option C: Auth Context Provider Check (Alternative)**
```typescript
// web/src/features/auth/context/AuthContext.tsx

export function AuthProvider({ children }) {
  const { user, isLoading } = useAuthSession();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && user && !user.email_verified) {
      // Allow access to verification page and logout
      const allowedPaths = ['/verify-email-required', '/logout'];
      const isAllowedPath = allowedPaths.some(path =>
        location.pathname.startsWith(path)
      );

      if (!isAllowedPath) {
        navigate({ to: '/verify-email-required' });
      }
    }
  }, [user, isLoading, location.pathname, navigate]);

  return <>{children}</>;
}
```

**Recommended Approach**: **Option B (Root Layout Guard)**

**Why**:
- ✅ DRY - Single source of truth
- ✅ Comprehensive - Automatically protects all nested routes
- ✅ Explicit - Clear route structure shows protected vs public
- ✅ Testable - Can test layout guard in isolation
- ✅ Maintainable - No need to remember to add guard to every route

**Routes That Should NOT Require Email Verification**:
```typescript
const publicRoutes = [
  '/login',
  '/signup',
  '/verify-email-required',
  '/verify-email', // Email verification handler
  '/logout',
  '/forgot-password',
  '/reset-password',
];
```

**Implementation Checklist**:
- [ ] Create `_authenticated` layout route with email verification check
- [ ] Move all protected routes under `_authenticated/` directory
- [ ] Create API error interceptor to handle `email_verification_required` errors
- [ ] Test that unverified users CANNOT access any protected route
- [ ] Test that unverified users CAN access `/verify-email-required` and `/logout`
- [ ] Verify infinite redirect loops don't occur

#### 2.7 Add API Error Interceptor for Backend Verification Errors
**Purpose**: Redirect users when backend returns `email_verification_required` error (defense in depth)

**Scenario**: User bypasses frontend guards or makes direct API call while unverified

**Solution**: Add global API error interceptor

```typescript
// web/src/lib/api/axios-instance.ts (or similar API client setup)

import axios from 'axios';
import { router } from '@/lib/router';

export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

// Response interceptor to handle email verification errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Check for email verification required error
    if (error.response?.status === 403) {
      const data = error.response?.data;

      if (data?.error === 'email_verification_required') {
        // Redirect to verification page
        router.navigate({ to: '/verify-email-required' });

        // Show toast notification
        toast.info("Please verify your email to continue");

        // Prevent error from propagating
        return Promise.reject({
          message: 'Email verification required',
          redirected: true,
        });
      }
    }

    return Promise.reject(error);
  }
);
```

**Alternative: React Query Error Handler**
```typescript
// web/src/lib/react-query.ts

import { QueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { toast } from 'sonner';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error: any) => {
        // Handle email verification errors globally
        if (error?.response?.data?.error === 'email_verification_required') {
          const navigate = useNavigate();
          navigate({ to: '/verify-email-required' });
          toast.info("Please verify your email to continue");
        }
      },
    },
    mutations: {
      onError: (error: any) => {
        // Handle email verification errors globally
        if (error?.response?.data?.error === 'email_verification_required') {
          const navigate = useNavigate();
          navigate({ to: '/verify-email-required' });
          toast.info("Please verify your email to continue");
        }
      },
    },
  },
});
```

**Why Both Frontend Guards AND API Interceptor?**

**Defense in Depth**:
1. **Frontend Layout Guard** (Primary): Prevents navigation to protected routes
2. **API Error Interceptor** (Backup): Catches cases where:
   - User directly calls API endpoints
   - Race conditions in auth state updates
   - User manipulates browser storage/cookies
   - Session expires while on protected page

**Result**: Even if frontend guards fail, backend + API interceptor ensure redirect

---

### Phase 3: Component Updates

#### 3.1 Remove Email Verification UI from Onboarding
**File**: `web/src/route-views/circles/components/CircleOnboardingContent.tsx`

**Changes**:
- **Remove** email verification section (lines with `!status.email_verified` check)
- **Remove** "Resend" button
- **Remove** "Refresh" button
- **Remove** email verification message
- **Remove** step indicator ("Step 1 of 2" becomes just form)
- Circle creation form should be **always enabled** (no email verification dependency)
- Keep "Skip" button functionality

**Removals**:
```typescript
// REMOVE THIS ENTIRE SECTION:
{!status.email_verified && (
  <div>
    <p>Verify your email at {status.email}</p>
    <button onClick={handleResend}>Resend</button>
    <button onClick={handleRefresh}>Refresh</button>
  </div>
)}
```

#### 3.2 Update Onboarding Controller
**File**: `web/src/features/circles/hooks/useCircleOnboardingController.ts`

**Changes**:
- **Remove** `canSubmit = status.email_verified` logic (line 36)
- Circle creation form should always be enabled
- **Remove** resend verification email logic
- **Remove** refresh verification status logic
- Keep circle creation and skip logic

**Removals**:
```typescript
// REMOVE:
const canSubmit = status.email_verified;
const handleResend = ...
const handleRefresh = ...
```

#### 3.3 Remove Email Verification UI from Settings
**File**: `web/src/features/profile/components/ProfileGeneralSettingsCard.tsx`

**Changes**:
- **Remove** email verification status display
- **Remove** "Email verified" / "Email not verified" labels
- **Remove** "Resend" button
- **Remove** "Refresh" button
- **Only show** email address (read-only)

**Removals**:
```typescript
// REMOVE verification status display:
{user.email_verified ? (
  <span>Email verified</span>
) : (
  <>
    <span>Email not verified</span>
    <button onClick={resendVerification}>Resend</button>
    <button onClick={refresh}>Refresh</button>
  </>
)}
```

**Keep**:
```typescript
// KEEP email display only:
<div>
  <label>Email</label>
  <span>{user.email}</span>
</div>
```

**Note**: Component creation covered in **Phase 2.1** with improved implementation (auto-polling, error handling, better UX)

---

### Phase 5: Type & Interface Updates

#### 5.1 Update API Response Types
**File**: `web/src/features/auth/types/auth.types.ts`

**Changes**:
- Add auto-login fields to verification response type (REQUIRED, not optional)
- Ensure `email_verified` is required (not optional) in `AuthUser`
- Add comprehensive type documentation
- Align with backend response structure

**Implementation**:
```typescript
/**
 * Response from email verification confirm endpoint.
 *
 * Includes auto-login tokens and user data.
 */
export interface EmailVerificationResponse {
  /** Success message */
  message: string;

  /** Redirect URL after verification (typically /circles/onboarding) */
  redirect_url: string;  // REQUIRED

  /** JWT access token for auto-login */
  access_token: string;  // REQUIRED

  /** Verified user data with email_verified: true */
  user: AuthUser;  // REQUIRED
}

/**
 * Authenticated user data.
 */
export interface AuthUser {
  id: number;
  username: string;
  email: string;

  /** Email verification status - REQUIRED field */
  email_verified: boolean;  // REQUIRED (not optional)

  first_name?: string;
  last_name?: string;

  /** Circle onboarding status */
  circle_onboarding_status?: "pending" | "completed" | "dismissed";

  /** Whether user needs to complete circle onboarding */
  needs_circle_onboarding?: boolean;
}

/**
 * Signup response type.
 */
export interface SignupResponse {
  message: string;
  access_token: string;

  /** User data including email_verified status */
  user: AuthUser;  // Includes email_verified for routing logic
}
```

**Type Safety Benefits**:
- ✅ Required fields enforce backend contract
- ✅ TypeScript catches missing response fields at compile time
- ✅ Auto-login flow guaranteed to have necessary data
- ✅ Consistent with implementation in Phase 2.3
- ✅ Self-documenting with TSDoc comments
- ✅ Prevents runtime `undefined` errors

---

### Phase 6: Cleanup Old Verification Flow Code

#### 6.1 Remove Old Email Verification Route (If Exists)
**Check for**: Old `/verify-email` success page route (not the handler)

**Files to Check**:
- `web/src/routes/verify-email.tsx` - Keep handler, remove any old success page
- Any old verification success components

**Action**: Remove any old static verification success pages (we now redirect to onboarding)

#### 6.2 Remove Unused Email Verification Components
**Files to Review & Clean**:

1. **CircleOnboardingContent.tsx** - Remove verification UI:
   ```typescript
   // DELETE entire email verification section:
   {!status.email_verified && (
     <>
       <div>Email verification UI</div>
       <button>Resend</button>
       <button>Refresh</button>
     </>
   )}
   ```

2. **ProfileGeneralSettingsCard.tsx** - Remove verification controls:
   ```typescript
   // DELETE verification status and buttons:
   {user.email_verified ? (
     <span>Verified badge</span>
   ) : (
     <>
       <span>Not verified badge</span>
       <button>Resend</button>
       <button>Refresh</button>
     </>
   )}
   ```

#### 6.3 Clean Up Onboarding Controller Hook
**File**: `web/src/features/circles/hooks/useCircleOnboardingController.ts`

**Remove**:
- `canSubmit = status.email_verified` logic
- `handleResend` function for verification email
- `handleRefresh` function to check verification status
- Any verification-related state variables
- Resend mutation if only used for onboarding

**Keep**:
- Circle creation logic
- Skip onboarding logic
- Form validation (non-email related)

#### 6.4 Clean Up Unused API Response Fields (Optional)
**File**: `mysite/users/views/onboarding.py`

**Consider Removing from Response** (if not used elsewhere):
- `email_verified` field from onboarding status response (now checked at backend)
- `email` field if not needed after cleanup

**Keep**:
- `status`, `needs_circle_onboarding`, `memberships_count`

#### 6.5 Remove Dead Code from EmailVerificationHandler
**File**: `web/src/features/auth/components/EmailVerificationHandler.tsx`

**Review for Old Code**:
- Remove any old success page rendering
- Remove any old redirect logic to verify success page
- Keep only: token verification + auto-login + redirect to onboarding

#### 6.6 Clean Up Unused Hooks (If Applicable)
**Check these hooks for usage**:

1. **useResendVerificationMutation** - Check if still used in:
   - ✅ Keep: Used in new `/verify-email-required` page
   - ❌ Remove: If only used in old onboarding/settings (now removed)

2. **useCircleOnboarding query** - Check if email verification fields needed:
   - May be able to remove email verification related fields from query
   - Check if `email` and `email_verified` fields used anywhere else

#### 6.7 Clean Up CSS/Styling (If Exists)
**Files to Check**:
- Any CSS specific to email verification UI in onboarding
- Any CSS for verification badges/buttons in settings
- Step indicator CSS if "Step 1 of 2" removed from onboarding

#### 6.8 Remove Old Comments & TODO Items
**Search for**:
- `// TODO: email verification`
- `// FIXME: verification`
- Old comments referencing verification in onboarding/settings
- Update any documentation comments about verification flow

#### 6.9 Clean Up Test Files (If Exist)
**Files to Update**:
- Tests for old onboarding verification UI
- Tests for old settings verification UI
- Tests for old verify success page
- Update integration tests for new flow

#### 6.10 Remove Unused Imports
**After cleanup, remove**:
- Unused email verification hooks in onboarding files
- Unused email verification components
- Unused verification utility functions
- Unused verification types/interfaces

#### 6.11 Backend Cleanup (Optional Optimization)
**File**: `mysite/users/views/onboarding.py`

**Consider Removing**:
- `email_verified` field from CircleOnboardingView GET response (now enforced by permission class)
- `email` field from response if no longer needed by frontend

**Why**: Reduces response payload size; email verification is enforced at permission layer

#### 6.12 Final Validation
**After all cleanup, verify**:
1. **No Circular Dependencies**: Check for import cycles introduced by new files
2. **Bundle Size Reduction**: Compare before/after bundle size (should be smaller)
3. **No Orphaned Files**: Search for files with 0 imports/references
4. **Consistent Terminology**: Ensure all "email verification" references use same wording
5. **Error Message Consistency**: Check all user-facing messages for clarity

---

## Cleanup Checklist

### Code Removal Tasks
- [ ] Remove old email verification UI from `CircleOnboardingContent.tsx`
- [ ] Remove old email verification UI from `ProfileGeneralSettingsCard.tsx`
- [ ] Remove `canSubmit = status.email_verified` from onboarding controller
- [ ] Remove `handleResend` verification logic from onboarding controller
- [ ] Remove `handleRefresh` verification logic from onboarding controller
- [ ] Remove step indicator ("Step 1 of 2") from onboarding if exists
- [ ] Remove any old static verification success page components
- [ ] Clean up unused imports in onboarding files
- [ ] Clean up unused imports in settings files
- [ ] Clean up unused imports in EmailVerificationHandler
- [ ] Remove unused verification-specific CSS/styling
- [ ] Search and remove TODO/FIXME comments about old verification
- [ ] Update or remove tests for old verification UI
- [ ] Check `useResendVerificationMutation` - remove if unused after cleanup
- [ ] Check if `email_verified` can be removed from onboarding API response
- [ ] Verify no dead code in EmailVerificationHandler component
- [ ] Remove any unused verification utility functions
- [ ] Remove unused verification types/interfaces if applicable
- [ ] Run linter and remove any unused variables flagged
- [ ] Search codebase for "email_verified" in UI - ensure all old UI removed
- [ ] Search codebase for "verification" - clean up old references

### Verification Tasks After Cleanup
- [ ] Run build to ensure no broken imports
- [ ] Run tests to ensure no test failures
- [ ] Search for console errors in dev environment
- [ ] Verify no unused exports warning in build
- [ ] Check bundle size (should be smaller after cleanup)
- [ ] Manual testing: verify no old UI appears anywhere
- [ ] Code review: ensure all old patterns removed

---

## Implementation Checklist

### Backend Tasks
- [ ] Create `EmailVerificationService` class in `mysite/auth/services/email_verification.py`
- [ ] Create `IsEmailVerified` permission class in `mysite/auth/permissions.py`
- [ ] Create `PublicUserSerializer` in `mysite/users/serializers.py`
- [ ] **CRITICAL**: Add `IsEmailVerified` to `DEFAULT_PERMISSION_CLASSES` in settings
- [ ] **CRITICAL**: Override permission_classes in auth views (ResendVerificationEmailView, etc.)
- [ ] Update `EmailVerificationConfirmView` to use service layer and generate JWT tokens
- [ ] Add `access_token`, `user`, and `redirect_url` to verification response
- [ ] Set HTTP-only refresh token cookie on verification (with domain/path)
- [ ] Add IP/device logging to verification audit event
- [ ] Update `SignupView` response to include `email_verified` field (REQUIRED, not optional)
- [x] ✅ OAuth verification - ALREADY IMPLEMENTED (no changes needed)
- [ ] Test email verification endpoint returns tokens and redirect URL
- [ ] Test auto-login works from email link (different browser/device)
- [ ] Test OAuth users are automatically marked as verified (should already work)
- [ ] **CRITICAL**: Test unverified user CANNOT access ANY API endpoint (circles, users, etc.)
- [ ] **CRITICAL**: Test unverified user CAN access auth endpoints (resend, verify)
- [ ] Test rate limiting on verification resend (5 per 15 min)
- [ ] Verify refresh token cookie is HTTP-only and secure with proper domain/path

### Frontend Tasks
- [ ] Create new route `/verify-email-required` with blocking page component
- [ ] **CRITICAL**: Create `_authenticated` layout route with global email verification guard
- [ ] **CRITICAL**: Move all protected routes under `_authenticated/` directory structure
- [ ] **CRITICAL**: Add API error interceptor to catch `email_verification_required` and redirect
- [ ] Create `requireEmailVerified` guard function (for individual route use if needed)
- [ ] Update `SignupCard` to redirect to `/verify-email-required` after signup (unless OAuth)
- [ ] Update `EmailVerificationHandler` to handle auto-login tokens
- [ ] Store access token from verification response in auth context
- [ ] Handle user data update from verification response
- [ ] Show toast notification: "Email verified successfully!"
- [ ] Redirect to `/circles/onboarding` after verification
- [ ] Remove email verification UI from `CircleOnboardingContent` component
- [ ] Remove email verification logic from `useCircleOnboardingController` hook
- [ ] Remove email verification UI from `ProfileGeneralSettingsCard` component
- [ ] Update TypeScript types for auto-login verification response
- [ ] Test complete flow: signup → verify page → email link → auto-login → onboarding
- [ ] Test auto-login from different browser/device
- [ ] Test OAuth signup skips verification page
- [ ] **CRITICAL**: Test unverified user CANNOT access ANY protected route (circles, settings, etc.)
- [ ] **CRITICAL**: Test unverified user gets REDIRECTED (not error) when accessing protected routes
- [ ] **CRITICAL**: Test unverified user CAN ONLY access /verify-email-required and /logout
- [ ] Test API interceptor redirects on backend 403 email_verification_required error
- [ ] Test toast appears when redirected via API interceptor
- [ ] Test that settings page no longer shows verification UI
- [ ] Test toast notification appears on verification
- [ ] Test refresh token cookie is set correctly
- [ ] Test no infinite redirect loops occur

### Testing Tasks
- [ ] Test signup redirects to verification required page
- [ ] Test verification required page shows correct email
- [ ] Test resend button works on verification required page
- [ ] Test refresh button checks status on verification required page
- [ ] Test clicking verify link redirects to onboarding (not verify page)
- [ ] Test toast appears when email is verified
- [ ] Test onboarding page has no verification UI
- [ ] Test settings page has no verification UI
- [ ] Test onboarding is blocked for unverified users (shows 403 or redirects)
- [ ] Test complete flow from signup to circle creation
- [ ] Test edge case: manually navigating to `/circles/onboarding` without verification

### Documentation Tasks
- [ ] Update user documentation about email verification requirement
- [ ] Update API documentation for verification endpoint changes
- [ ] Document new route and guard functions
- [ ] Add comments explaining verification flow in code

---

## Deployment Notes

**✅ No Migration Required:**
- App is not yet deployed to production
- Can make breaking changes without backward compatibility
- No existing users to migrate
- `email_verified` field already exists on User model

**Cleanup Strategy:**
- Aggressive cleanup of old verification flow code
- Remove all unused routes, components, and logic
- No need to preserve old UI or backward compatibility

---

## Security Considerations for Auto-Login

### Why Auto-Login via Email Link is Secure

**✅ Industry Standard Practice:**
- Same security model as password reset links
- Used by major services: GitHub, Gmail, Slack, etc.
- Email ownership proves identity

**✅ Current Security Measures:**
| Security Layer | Implementation | Status |
|----------------|----------------|---------|
| Token Randomness | Cryptographically secure random tokens | ✅ Existing |
| Single-Use Tokens | `pop_token()` invalidates after use | ✅ Existing |
| Time Expiration | TTL limits attack window | ✅ Existing |
| Rate Limiting | 10 requests per 15 min per IP/token | ✅ Existing |
| Audit Logging | Track verification events with IP/device | ✅ Enhanced |
| HTTPS Only | Secure transport layer | ✅ Required |
| HTTP-Only Cookie | Refresh token not accessible to JS | ✅ New |
| SameSite Cookie | CSRF protection | ✅ New |

**✅ Additional Protections:**
1. **Email Security**: Relies on email provider's security (same as password reset)
2. **Token Invalidation**: One-time use prevents replay attacks
3. **Short Expiration**: Time-limited tokens reduce attack window
4. **Audit Trail**: IP and device logging for security monitoring
5. **Fresh Tokens**: New JWT generated each time (not reusing old sessions)

**⚠️ Potential Risks & Mitigations:**
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Email interception | Low | HTTPS, email provider TLS |
| Token theft from email | Low | Single-use + expiration |
| Malicious email access | Medium | User responsibility (same as password reset) |
| Session hijacking | Low | HTTP-only cookies, secure flag |

### Best Practices Implemented
- ✅ Generate fresh tokens on verification (not reuse signup session)
- ✅ Invalidate token immediately after use
- ✅ Set short expiration time (configurable, recommend 24-48 hours)
- ✅ Use HTTPS-only cookies for refresh tokens
- ✅ Log security events for audit and monitoring
- ✅ Rate limit verification attempts

### Comparison with Alternatives

| Method | Security | UX | Implementation |
|--------|----------|-----|----------------|
| **Auto-login via email** | High | Excellent | ✅ Recommended |
| Manual login after verify | High | Poor | Not recommended |
| Magic link (passwordless) | High | Good | Similar security |
| Password reset flow | High | Good | Same security model |

---

## Security Review & Hardening

### 🔴 CRITICAL Security Issues (MUST FIX)

**1. Missing Rate Limiting on Verification Confirm Endpoint**
- **Location**: `mysite/auth/views.py` - EmailVerificationConfirmView.post()
- **Issue**: No rate limiting on token verification endpoint
- **Risk**: Brute-force attacks on verification tokens
- **Fix**: Add rate limiting decorator
```python
from django_ratelimit.decorators import ratelimit

@method_decorator(ratelimit(key='ip', rate='10/15m', method='POST'), name='dispatch')
class EmailVerificationConfirmView(APIView):
    # ...
```

**2. Client IP Spoofing Vulnerability**
- **Location**: `mysite/auth/views.py` lines 268-275
- **Issue**: `X-Forwarded-For` header is easily spoofed
- **Risk**: Bypass IP-based rate limiting
- **Fix**: Use Django IPWare library
```python
from ipware import get_client_ip

def _get_client_ip(self, request):
    client_ip, is_routable = get_client_ip(request)
    return client_ip if client_ip else request.META.get('REMOTE_ADDR')
```

**3. Token Reuse Not Prevented**
- **Location**: `mysite/auth/services/email_verification.py` lines 140-145
- **Issue**: Re-verification only logs warning but doesn't block
- **Risk**: Token could be used multiple times if pop_token() fails
- **Fix**: Block re-verification attempts
```python
if user.email_verified:
    raise ValueError("Email already verified")  # Block, don't just warn
```

**4. Race Condition in Verification**
- **Location**: `mysite/auth/services/email_verification.py` lines 122-156
- **Issue**: Multiple simultaneous verification attempts could both succeed
- **Risk**: Token reuse, audit log inconsistencies
- **Fix**: Use database row locking
```python
@transaction.atomic
def verify_and_login(self, user) -> Tuple[str, str]:
    # Lock user row to prevent race conditions
    user = User.objects.select_for_update().get(pk=user.pk)

    if user.email_verified:
        raise ValueError("Email already verified")

    user.email_verified = True
    user.save(update_fields=["email_verified"])
    # ...
```

**5. Frontend Redirect Loop Risk**
- **Location**: API error interceptor lines 1220-1311
- **Issue**: No protection against infinite redirects
- **Risk**: Browser hangs if verification page calls protected API
- **Fix**: Check current location before redirecting
```typescript
if (data?.error === 'email_verification_required') {
  // Prevent redirect loop
  if (window.location.pathname !== '/verify-email-required') {
    router.navigate({ to: '/verify-email-required' });
    toast.info("Please verify your email to continue");
  }
}
```

**6. Missing Automated Test for Permission Overrides**
- **Location**: Global permission configuration lines 526-550
- **Issue**: Requires manual override for each exempt endpoint
- **Risk**: Forgetting to override blocks legitimate endpoints
- **Fix**: Create automated test
```python
def test_unverified_user_can_access_auth_endpoints():
    """Ensure auth endpoints work for unverified users"""
    exempt_endpoints = [
        '/api/auth/login/',
        '/api/auth/signup/',
        '/api/auth/verify-email/',
        '/api/auth/resend-verification/',
        '/api/auth/google/',
    ]
    # Test each endpoint is accessible for unverified users
```

### 🟡 HIGH Priority Security Issues

**7. Error Message Information Leakage**
- **Location**: `mysite/auth/views.py` lines 249-266
- **Issue**: Different errors reveal if account exists and is active/inactive
- **Risk**: User enumeration attacks
- **Fix**: Use generic error messages
```python
except ValueError as e:
    logger.warning(f"Email verification validation failed: {e}")
    return Response(
        {"detail": "Email verification failed. Please try again."},  # Generic message
        status=status.HTTP_400_BAD_REQUEST,
    )
```

**8. Weak Cookie SameSite Setting**
- **Location**: Cookie configuration lines 225-234
- **Issue**: `SameSite=Lax` allows some cross-site requests
- **Risk**: CSRF attacks in certain scenarios
- **Fix**: Use `SameSite=Strict` for refresh tokens
```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    samesite="Strict",  # Changed from Lax
    # ... other settings
)
```

**9. Missing Failed Verification Audit Logging**
- **Location**: `mysite/auth/views.py` lines 237-245
- **Issue**: Only successful verifications are logged
- **Risk**: Can't detect brute-force or suspicious patterns
- **Fix**: Log all verification attempts
```python
# Log failed attempts
except Exception as e:
    AuditLog.objects.create(
        user=user,
        action="email_verification_failed",
        ip_address=self._get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata={"error": str(e)},
    )
    logger.error(f"Email verification failed for user {user.id}: {e}", exc_info=True)
```

**10. No Token Entropy Specification**
- **Issue**: Document doesn't specify token generation method
- **Risk**: Weak tokens could be brute-forced
- **Fix**: Document token requirements
```python
# In token generation service - ensure using:
import secrets
token = secrets.token_urlsafe(32)  # 256-bit entropy minimum
```

**11. Missing Device/Session Binding**
- **Issue**: Anyone with token link can verify from any device
- **Risk**: Stolen email links can be used from attacker's device
- **Mitigation**: Consider optional device fingerprinting for high-security scenarios

**12. No Explicit CSRF Token Validation**
- **Issue**: Only relies on SameSite cookie for CSRF protection
- **Risk**: CSRF attacks possible in some browsers/scenarios
- **Fix**: Add explicit CSRF token validation
```python
from django.views.decorators.csrf import csrf_protect

@method_decorator(csrf_protect, name='dispatch')
class EmailVerificationConfirmView(APIView):
    # ...
```

### 🟢 MODERATE Priority Security Issues

**13. Resend Email Abuse Risk**
- **Location**: ResendVerificationEmailView lines 539-550
- **Issue**: Rate limiting mentioned but no CAPTCHA
- **Risk**: Email bombing attacks if rate limiting bypassed
- **Fix**: Add CAPTCHA after 2-3 attempts
```python
# Add CAPTCHA verification after threshold
if request.session.get('resend_count', 0) >= 3:
    # Require CAPTCHA verification
    verify_captcha(request)
```

**14. No Runtime Type Validation**
- **Location**: TypeScript types lines 1407-1467
- **Issue**: TypeScript types don't validate at runtime
- **Risk**: Missing or malformed data causes crashes
- **Fix**: Use Zod for runtime validation
```typescript
import { z } from 'zod';

const EmailVerificationResponseSchema = z.object({
  message: z.string(),
  redirect_url: z.string(),
  access_token: z.string(),
  user: z.object({
    id: z.number(),
    email_verified: z.boolean(),
    // ...
  }),
});

// Validate response
const validatedResponse = EmailVerificationResponseSchema.parse(response);
```

**15. OAuth Email Verification Trust**
- **Location**: OAuth service lines 585-586
- **Issue**: Document doesn't show ID token signature verification
- **Risk**: If not implemented, could accept forged claims
- **Action**: Verify implementation properly validates Google ID token signature

**16. No Token Invalidation on Password Change**
- **Issue**: Old verification tokens remain valid after password change
- **Risk**: Compromised old emails could still verify account
- **Fix**: Invalidate all pending verification tokens on password change
```python
# In password change handler
def change_password(user, new_password):
    # Invalidate all pending verification tokens
    VerificationToken.objects.filter(user=user, used=False).delete()
    user.set_password(new_password)
    user.save()
```

**17. Permission Class Implementation Inconsistency**
- **Location**: Lines 316-320 vs 426-433
- **Issue**: Two different implementations shown
- **Risk**: DRF might not handle self.message approach correctly
- **Fix**: Use only raise PermissionDenied() approach
```python
# Use this approach (correct):
if not user.email_verified:
    raise PermissionDenied({
        'error': 'email_verification_required',
        'detail': 'Email verification required.',
        'redirect_to': '/verify-email-required'
    })

# NOT this approach:
# self.message = {...}  # Don't use this
# return False
```

**18. No Verification Token Scope Validation**
- **Issue**: Doesn't explicitly verify token is scoped to correct user
- **Risk**: Token mixup could verify wrong account
- **Fix**: Add assertion in token validation
```python
# In token validation
if token.user_id != user.id:
    raise ValueError("Token user mismatch")
```

**19. Missing Security Headers**
- **Issue**: No mention of security headers
- **Risk**: Clickjacking, XSS attacks
- **Fix**: Add security headers to responses
```python
# In settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
```

**20. No Token Expiration Monitoring**
- **Issue**: No alerting when tokens expire unused
- **Risk**: Poor UX if users don't know to request new token
- **Recommendation**: Add monitoring for expired unused tokens

### Security Implementation Checklist

**CRITICAL (Must Fix Before Production)**:
- [ ] Add rate limiting to EmailVerificationConfirmView (10/15min per IP)
- [ ] Fix IP detection using ipware library
- [ ] Block token reuse after verification (raise error, not just log)
- [ ] Add select_for_update() to prevent race conditions
- [ ] Add redirect loop prevention in API interceptor
- [ ] Create automated test for permission override coverage

**HIGH Priority**:
- [ ] Use generic error messages (prevent user enumeration)
- [ ] Change SameSite cookie to Strict
- [ ] Log all verification attempts (success + failure)
- [ ] Document token generation uses secrets.token_urlsafe(32)
- [ ] Add device fingerprinting for high-security mode (optional)
- [ ] Add CSRF token validation to verification endpoint

**RECOMMENDED**:
- [ ] Add CAPTCHA to resend after 3 attempts
- [ ] Add Zod runtime validation for API responses
- [ ] Verify OAuth ID token signature validation is implemented
- [ ] Invalidate verification tokens on password change
- [ ] Standardize permission class implementation
- [ ] Add token scope validation assertion
- [ ] Add security headers (CSP, X-Frame-Options, HSTS)
- [ ] Add monitoring for expired unused tokens

### Security Testing Requirements

**Authentication Tests**:
- [ ] Test token cannot be reused after verification
- [ ] Test concurrent verification attempts are prevented
- [ ] Test rate limiting on verification endpoint
- [ ] Test verification with expired token
- [ ] Test verification with invalid token
- [ ] Test verification with wrong user's token

**Authorization Tests**:
- [ ] Test unverified user CANNOT access protected APIs
- [ ] Test unverified user CAN access auth endpoints
- [ ] Test permission override for all exempt endpoints
- [ ] Test redirect instead of 403 error for better UX

**Abuse Prevention Tests**:
- [ ] Test IP spoofing doesn't bypass rate limiting
- [ ] Test resend email rate limiting (5 per 15min)
- [ ] Test CAPTCHA appears after threshold
- [ ] Test email bombing prevention

**Error Handling Tests**:
- [ ] Test generic errors don't leak user existence
- [ ] Test redirect loop prevention works
- [ ] Test graceful degradation on failures

---

## Security Best Practice Implementations

This section provides production-ready, complete implementations for all critical and high-priority security fixes.

### 1. Complete Email Verification Service with Security Hardening

**File**: `mysite/auth/services/email_verification.py`

```python
"""
Email verification service layer with comprehensive security controls.

Security features:
- Token reuse prevention
- Race condition protection via row locking
- Audit logging (success + failure)
- Generic error messages
- Token scope validation
"""
import logging
from typing import Tuple, Optional
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from mysite.users.models import User
from mysite.audit.models import AuditLog

logger = logging.getLogger(__name__)


class EmailVerificationError(Exception):
    """Base exception for email verification errors."""
    pass


class EmailVerificationService:
    """Service for secure email verification operations."""

    @transaction.atomic
    def verify_and_login(
        self,
        user: User,
        ip_address: str,
        user_agent: str,
    ) -> Tuple[str, str]:
        """
        Verify user email and generate fresh auth tokens with security controls.

        Security measures:
        - Database row locking to prevent race conditions
        - Blocks re-verification attempts (token reuse prevention)
        - Validates user state (active check)
        - Generates fresh JWT tokens
        - Comprehensive audit logging

        Args:
            user: User instance to verify
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            EmailVerificationError: If verification fails for any reason
        """
        try:
            # Lock user row to prevent race conditions (CRITICAL)
            user = User.objects.select_for_update().get(pk=user.pk)

            # Validation 1: User must be active
            if not user.is_active:
                self._log_verification_failure(
                    user, ip_address, user_agent, "inactive_user"
                )
                raise EmailVerificationError("Verification failed")

            # Validation 2: Block re-verification (token reuse prevention)
            if user.email_verified:
                self._log_verification_failure(
                    user, ip_address, user_agent, "already_verified"
                )
                raise EmailVerificationError("Email already verified")

            # Update user email_verified flag
            user.email_verified = True
            user.save(update_fields=["email_verified"])

            # Generate fresh JWT tokens for auto-login
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Success audit logging
            self._log_verification_success(user, ip_address, user_agent)

            logger.info(
                f"Email verified and auto-login successful for user {user.id}",
                extra={"user_id": user.id, "ip_address": ip_address}
            )

            return access_token, refresh_token

        except User.DoesNotExist:
            # Should never happen, but handle gracefully
            logger.error("User not found during verification")
            raise EmailVerificationError("Verification failed")

        except Exception as e:
            # Catch any unexpected errors
            self._log_verification_failure(
                user, ip_address, user_agent, f"unexpected_error: {str(e)}"
            )
            logger.error(
                f"Unexpected error during verification: {e}",
                exc_info=True,
                extra={"user_id": user.id if user else None}
            )
            raise EmailVerificationError("Verification failed")

    def _log_verification_success(
        self, user: User, ip_address: str, user_agent: str
    ) -> None:
        """Log successful verification attempt."""
        AuditLog.objects.create(
            user=user,
            action="email_verified_with_auto_login",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"auto_login": True, "status": "success"},
        )

    def _log_verification_failure(
        self, user: User, ip_address: str, user_agent: str, reason: str
    ) -> None:
        """Log failed verification attempt for security monitoring."""
        AuditLog.objects.create(
            user=user,
            action="email_verification_failed",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"status": "failed", "reason": reason},
        )
```

### 2. Hardened Email Verification View with Rate Limiting

**File**: `mysite/auth/views.py` - Update EmailVerificationConfirmView

```python
"""Email verification confirmation endpoint with security hardening."""
import logging
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.decorators import ratelimit
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ipware import get_client_ip

from .services.email_verification import EmailVerificationService, EmailVerificationError
from .serializers import EmailVerificationConfirmSerializer
from ..users.serializers import PublicUserSerializer

logger = logging.getLogger(__name__)


@method_decorator(
    ratelimit(
        key='ip',
        rate='10/15m',
        method='POST',
        block=True
    ),
    name='dispatch'
)
@method_decorator(csrf_protect, name='dispatch')
class EmailVerificationConfirmView(APIView):
    """
    Verify email token and auto-login user.

    Security features:
    - Rate limiting: 10 attempts per 15 minutes per IP
    - CSRF protection via csrf_protect decorator
    - Secure IP detection (ipware library)
    - Generic error messages (prevent user enumeration)
    - Comprehensive audit logging
    - Secure cookie configuration

    Returns JWT tokens and redirects to onboarding.
    """
    permission_classes = [AllowAny]  # Token validation replaces auth

    def post(self, request):
        """
        Verify email token and auto-login user.

        Request:
            {
                "token": "verification_token_string"
            }

        Response (Success):
            {
                "message": "Email verified successfully.",
                "redirect_url": "/circles/onboarding",
                "access_token": "jwt_access_token",
                "user": { ... }
            }

        Response (Error):
            {
                "detail": "Email verification failed. Please try again."
            }
        """
        # Get secure client IP (prevents X-Forwarded-For spoofing)
        client_ip = self._get_secure_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Validate verification token
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Invalid verification token format",
                extra={"ip_address": client_ip}
            )
            return Response(
                {"detail": "Email verification failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]

        try:
            # Use service layer for verification + token generation
            service = EmailVerificationService()
            access_token, refresh_token = service.verify_and_login(
                user=user,
                ip_address=client_ip,
                user_agent=user_agent,
            )

            # Build response with tokens and safe user data
            response = Response(
                {
                    "message": "Email verified successfully.",
                    "redirect_url": "/circles/onboarding",
                    "access_token": access_token,
                    "user": PublicUserSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

            # Set secure refresh token cookie
            self._set_secure_refresh_cookie(response, refresh_token)

            return response

        except EmailVerificationError as e:
            # Generic error message to prevent user enumeration
            logger.warning(
                f"Email verification failed for user {user.id}",
                extra={"user_id": user.id, "ip_address": client_ip}
            )
            return Response(
                {"detail": "Email verification failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Unexpected error during email verification: {e}",
                exc_info=True,
                extra={"user_id": user.id, "ip_address": client_ip}
            )
            return Response(
                {
                    "detail": "Email verification failed. Please contact support if this continues."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_secure_client_ip(self, request) -> str:
        """
        Get client IP using ipware library (prevents X-Forwarded-For spoofing).

        Uses ipware to properly handle proxy chains and prevent IP spoofing.
        """
        client_ip, is_routable = get_client_ip(request)
        if client_ip is None:
            # Fallback to REMOTE_ADDR if ipware fails
            client_ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return client_ip

    def _set_secure_refresh_cookie(self, response: Response, refresh_token: str) -> None:
        """
        Set refresh token cookie with security best practices.

        Security features:
        - HttpOnly: Prevents JavaScript access
        - Secure: HTTPS only
        - SameSite=Strict: Prevents CSRF attacks
        - Proper domain/path scoping
        """
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=60 * 60 * 24 * 7,  # 7 days
            httponly=True,  # Not accessible via JavaScript (XSS protection)
            secure=True,  # HTTPS only
            samesite="Strict",  # CSRF protection (changed from Lax)
            domain=getattr(settings, 'SESSION_COOKIE_DOMAIN', None),
            path="/",
        )
```

### 3. Secure Token Generation and Management

**File**: `mysite/auth/services/token_service.py` (NEW)

```python
"""
Secure token generation and management service.

Ensures cryptographically secure tokens with proper entropy.
"""
import secrets
from typing import Tuple
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache

# Token configuration
TOKEN_LENGTH = 32  # 256-bit entropy
TOKEN_TTL_HOURS = 48  # 48 hour expiration


class TokenService:
    """Service for secure token generation and validation."""

    @staticmethod
    def generate_verification_token(user_id: int) -> Tuple[str, str]:
        """
        Generate cryptographically secure verification token.

        Uses secrets.token_urlsafe for 256-bit entropy.
        Stores token in cache with TTL for validation.

        Args:
            user_id: User ID to associate with token

        Returns:
            Tuple of (token, cache_key)
        """
        # Generate cryptographically secure random token
        token = secrets.token_urlsafe(TOKEN_LENGTH)  # 256-bit entropy

        # Create cache key for token storage
        cache_key = f"email_verification:{token}"

        # Store token with TTL
        cache.set(
            cache_key,
            {
                "user_id": user_id,
                "created_at": timezone.now().isoformat(),
            },
            timeout=60 * 60 * TOKEN_TTL_HOURS,  # 48 hours
        )

        return token, cache_key

    @staticmethod
    def validate_and_consume_token(token: str) -> int:
        """
        Validate token and consume it (single-use).

        Args:
            token: Verification token to validate

        Returns:
            user_id if token is valid

        Raises:
            ValueError: If token is invalid or expired
        """
        cache_key = f"email_verification:{token}"

        # Get token data (atomic operation)
        token_data = cache.get(cache_key)

        if not token_data:
            raise ValueError("Invalid or expired verification token")

        # Delete token immediately (single-use)
        cache.delete(cache_key)

        # Validate token data structure
        user_id = token_data.get("user_id")
        if not user_id:
            raise ValueError("Invalid token data")

        return user_id

    @staticmethod
    def invalidate_user_tokens(user_id: int) -> None:
        """
        Invalidate all pending verification tokens for a user.

        Useful when user changes password or requests new token.
        """
        # Note: Requires cache key pattern matching
        # Implementation depends on cache backend
        # For Redis: SCAN + DEL pattern matching
        # For simple cases: Track tokens in database
        pass
```

### 4. Updated Permission Class with Proper Error Handling

**File**: `mysite/auth/permissions.py`

```python
"""Custom DRF permissions for authentication with security best practices."""
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsEmailVerified(BasePermission):
    """
    Permission that requires authenticated user with verified email.

    Raises PermissionDenied with specific error code that frontend
    intercepts and redirects to /verify-email-required.

    Security features:
    - Prevents access to protected resources for unverified users
    - Returns structured error for frontend redirect
    - Applies to ALL HTTP methods (GET, POST, PUT, DELETE, etc.)

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsEmailVerified]
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated, active, and email verified.

        Returns:
            True if user has verified email, raises PermissionDenied otherwise
        """
        # Check authentication first
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is active
        if not request.user.is_active:
            return False

        # Check email verification
        if not getattr(request.user, 'email_verified', False):
            # Raise PermissionDenied with structured error
            # Frontend API interceptor catches this and redirects
            raise PermissionDenied({
                'error': 'email_verification_required',
                'detail': 'Email verification required to access this resource.',
                'redirect_to': '/verify-email-required'
            })

        return True
```

### 5. Frontend API Interceptor with Redirect Loop Prevention

**File**: `web/src/lib/api/axios-instance.ts`

```typescript
/**
 * Axios instance with security-hardened error handling.
 *
 * Features:
 * - Email verification redirect with loop prevention
 * - Runtime response validation
 * - Secure credential handling
 */
import axios, { AxiosError } from 'axios';
import { router } from '@/lib/router';
import { toast } from 'sonner';

export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,  // Include cookies
  timeout: 30000,  // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track if we've already redirected to prevent loops
let hasRedirectedToVerification = false;

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Reset redirect flag on successful response
    hasRedirectedToVerification = false;
    return response;
  },
  (error: AxiosError) => {
    // Check for email verification required error
    if (error.response?.status === 403) {
      const data = error.response?.data as any;

      if (data?.error === 'email_verification_required') {
        // Prevent redirect loop (CRITICAL)
        const currentPath = window.location.pathname;
        const isOnVerificationPage = currentPath === '/verify-email-required';

        // Only redirect if not already on verification page
        if (!isOnVerificationPage && !hasRedirectedToVerification) {
          hasRedirectedToVerification = true;

          // Redirect to verification page
          router.navigate({ to: '/verify-email-required' });

          // Show user-friendly notification
          toast.info("Please verify your email to continue");

          // Return custom error to prevent further error handling
          return Promise.reject({
            message: 'Email verification required',
            redirected: true,
            code: 'EMAIL_VERIFICATION_REQUIRED',
          });
        }
      }
    }

    // Handle other errors normally
    return Promise.reject(error);
  }
);

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    // Add CSRF token if available
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Get CSRF token from cookie.
 */
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');

  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) {
      return decodeURIComponent(value);
    }
  }

  return null;
}
```

### 6. Runtime Response Validation with Zod

**File**: `web/src/features/auth/schemas/verification.schema.ts` (NEW)

```typescript
/**
 * Runtime validation schemas for email verification responses.
 *
 * Uses Zod for type-safe runtime validation to prevent crashes
 * from malformed API responses.
 */
import { z } from 'zod';

/**
 * Schema for email verification confirm response.
 */
export const EmailVerificationResponseSchema = z.object({
  message: z.string(),
  redirect_url: z.string().url(),
  access_token: z.string().min(20),  // JWT tokens are long
  user: z.object({
    id: z.number().positive(),
    username: z.string().min(1),
    email: z.string().email(),
    email_verified: z.boolean(),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    needs_circle_onboarding: z.boolean().optional(),
    circle_onboarding_status: z.enum(['pending', 'completed', 'dismissed']).optional(),
  }),
});

/**
 * Infer TypeScript type from schema.
 */
export type EmailVerificationResponse = z.infer<typeof EmailVerificationResponseSchema>;

/**
 * Schema for resend verification email response.
 */
export const ResendVerificationResponseSchema = z.object({
  message: z.string(),
  detail: z.string().optional(),
});

export type ResendVerificationResponse = z.infer<typeof ResendVerificationResponseSchema>;
```

**File**: `web/src/features/auth/hooks/useVerifyEmailConfirm.ts` - Updated with validation

```typescript
/**
 * Hook for email verification with runtime validation.
 */
import { useMutation } from '@tanstack/react-query';
import { authService } from '@/features/auth/services/authService';
import {
  EmailVerificationResponseSchema,
  type EmailVerificationResponse
} from '../schemas/verification.schema';

interface UseVerifyEmailConfirmOptions {
  onSuccess?: (data: EmailVerificationResponse) => void;
  onError?: (error: any) => void;
}

export function useVerifyEmailConfirm(options?: UseVerifyEmailConfirmOptions) {
  return useMutation({
    mutationFn: async (token: string) => {
      const response = await authService.verifyEmailConfirm({ token });

      // Runtime validation (CRITICAL - prevents crashes from bad data)
      try {
        const validatedResponse = EmailVerificationResponseSchema.parse(response);
        return validatedResponse;
      } catch (validationError) {
        console.error('Invalid verification response:', validationError);
        throw new Error('Invalid response from server. Please try again.');
      }
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}
```

### 7. Automated Permission Override Test

**File**: `mysite/auth/tests/test_permissions.py` (NEW)

```python
"""
Tests for email verification permission system.

Ensures unverified users can only access auth endpoints.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from mysite.users.models import User


class EmailVerificationPermissionTests(TestCase):
    """Test email verification permission enforcement."""

    def setUp(self):
        """Create test users and client."""
        self.client = APIClient()

        # Create verified user
        self.verified_user = User.objects.create_user(
            username='verified',
            email='verified@example.com',
            password='testpass123',
            email_verified=True
        )

        # Create unverified user
        self.unverified_user = User.objects.create_user(
            username='unverified',
            email='unverified@example.com',
            password='testpass123',
            email_verified=False
        )

    def test_unverified_user_can_access_auth_endpoints(self):
        """
        CRITICAL: Ensure auth endpoints work for unverified users.

        These endpoints MUST be accessible to unverified users:
        - Login
        - Signup
        - Verify email
        - Resend verification
        - OAuth endpoints
        - Password reset
        """
        # Login as unverified user
        self.client.force_authenticate(user=self.unverified_user)

        # Define exempt endpoints (must be accessible)
        exempt_endpoints = [
            ('auth:login', {}),
            ('auth:signup', {}),
            ('auth:verify-email', {}),
            ('auth:resend-verification', {}),
            ('auth:google-oauth-initiate', {}),
            ('auth:password-reset-request', {}),
        ]

        for endpoint_name, kwargs in exempt_endpoints:
            url = reverse(endpoint_name, kwargs=kwargs)

            # Try GET request (if supported)
            response = self.client.get(url)
            self.assertNotEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Unverified user should access {endpoint_name}"
            )

    def test_unverified_user_cannot_access_protected_endpoints(self):
        """
        CRITICAL: Ensure protected endpoints block unverified users.

        Unverified users should NOT access:
        - Onboarding
        - Circles
        - Profile/Settings
        - Any protected resource
        """
        # Login as unverified user
        self.client.force_authenticate(user=self.unverified_user)

        # Define protected endpoints
        protected_endpoints = [
            ('circles:onboarding', {}),
            ('circles:list', {}),
            ('users:profile', {}),
            ('users:settings', {}),
        ]

        for endpoint_name, kwargs in protected_endpoints:
            url = reverse(endpoint_name, kwargs=kwargs)
            response = self.client.get(url)

            # Should return 403 with email_verification_required error
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Unverified user should NOT access {endpoint_name}"
            )

            # Check error code for frontend redirect
            if response.status_code == 403:
                data = response.json()
                self.assertEqual(
                    data.get('error'),
                    'email_verification_required',
                    f"Should return email_verification_required error for {endpoint_name}"
                )

    def test_verified_user_can_access_all_endpoints(self):
        """Ensure verified users can access all protected endpoints."""
        # Login as verified user
        self.client.force_authenticate(user=self.verified_user)

        protected_endpoints = [
            ('circles:onboarding', {}),
            ('circles:list', {}),
            ('users:profile', {}),
        ]

        for endpoint_name, kwargs in protected_endpoints:
            url = reverse(endpoint_name, kwargs=kwargs)
            response = self.client.get(url)

            # Should NOT be blocked by email verification
            self.assertNotEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Verified user should access {endpoint_name}"
            )
```

### 8. Security Headers Configuration

**File**: `mysite/config/settings/base.py` - Add security headers

```python
"""Security headers configuration."""

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (HTTP Strict Transport Security)
# Only enable in production with HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SSL/HTTPS Settings
SECURE_SSL_REDIRECT = True  # Redirect HTTP to HTTPS
SESSION_COOKIE_SECURE = True  # HTTPS only for session cookies
CSRF_COOKIE_SECURE = True  # HTTPS only for CSRF cookies

# Content Security Policy (CSP)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Adjust as needed
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)  # Prevent framing

# Cookie Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Additional Security Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

### 9. Token Invalidation on Password Change

**File**: `mysite/users/views/password.py` - Add to password change view

```python
"""Password change with token invalidation."""
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


class ChangePasswordView(APIView):
    """Change user password and invalidate verification tokens."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Change password and invalidate all pending verification tokens.

        Security: Prevents old verification tokens from being used
        after password change.
        """
        user = request.user

        # Validate current password
        current_password = request.data.get('current_password')
        if not user.check_password(current_password):
            return Response(
                {'detail': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate new password
        new_password = request.data.get('new_password')
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Change password
        user.set_password(new_password)
        user.save()

        # Invalidate all pending verification tokens for this user
        self._invalidate_verification_tokens(user.id)

        # Log password change
        logger.info(f"Password changed for user {user.id}")

        return Response({'message': 'Password changed successfully'})

    def _invalidate_verification_tokens(self, user_id: int):
        """
        Invalidate all pending verification tokens for a user.

        Note: Implementation depends on how tokens are stored.
        If using cache with pattern matching, scan and delete.
        If using database, delete all unused tokens for user.
        """
        # For cache-based tokens (example with Redis pattern matching)
        # This requires cache backend that supports pattern matching
        pattern = f"email_verification:*"
        # Scan cache and delete tokens belonging to this user
        # Implementation varies by cache backend

        # Alternative: Track tokens in database for easy invalidation
        # VerificationToken.objects.filter(user_id=user_id, used=False).delete()
        pass
```

---

## Success Metrics

- ✅ 100% of new signups must verify email before accessing onboarding
- ✅ Email verification UI removed from onboarding page
- ✅ Email verification UI removed from settings page
- ✅ Verification link redirects to onboarding with toast notification
- ✅ No console errors or broken links in verification flow
- ✅ User testing confirms clearer, simpler flow

---

## Timeline Estimate

| Phase | Estimated Time | Complexity |
|-------|----------------|------------|
| Phase 1: Backend Changes | 3-4 hours | Medium-High |
| **Phase 1.5: Security Hardening** | **4-6 hours** | **High** |
| Phase 2: Routing Changes | 3-4 hours | Medium-High |
| Phase 3: Component Updates | 3-4 hours | Medium |
| Phase 4: Guards & Middleware | 2-3 hours | Medium |
| Phase 5: Type Updates | 1-2 hours | Low-Medium |
| **Phase 6: Cleanup Old Code** | **2-3 hours** | **Low-Medium** |
| **Security Testing** | **4-5 hours** | **High** |
| Integration Testing & QA | 3-4 hours | Medium |
| **Total** | **25-35 hours** | **Medium-High** |

**Notes**:
- Security hardening is CRITICAL and includes implementing all 6 critical fixes (rate limiting, IP detection, token reuse prevention, race condition fixes, redirect loop prevention, automated tests)
- Security testing phase validates all security controls work correctly
- Timeline increased from 15-21 to 25-35 hours to account for comprehensive security implementation
- Do NOT skip security hardening phase - contains critical production blockers

---

## Questions & Clarifications

### ✅ Resolved
1. **Resend rate limiting**: ✅ **YES** - Keep same rate limits (5 per 15 min per IP/identifier)
2. **OAuth users**: ✅ **NO** - OAuth users skip email verification (Google pre-verifies)
3. **Auto-login security**: ✅ **YES** - Secure to auto-login via verify link (same as password reset)

### ✅ All Questions Resolved
1. **Session expiry**: Auto-login handles this by generating fresh tokens ✅
2. **Logout behavior**: Yes, show logout link on verification required page ✅
3. **Email change**: N/A - Users cannot change their email (email is immutable) ✅
4. **Admin users**: Admin accounts also require email verification (no exemptions) ✅
5. **Existing unverified users**: N/A - No existing users (app not yet deployed) ✅

---

## Files to Modify - Summary

### Backend Files - Create New
1. `mysite/auth/services/email_verification.py` - NEW service layer with security hardening
2. `mysite/auth/services/token_service.py` - NEW secure token generation service (256-bit entropy)
3. `mysite/auth/permissions.py` - NEW IsEmailVerified permission class
4. `mysite/auth/tests/test_permissions.py` - NEW automated permission override tests
5. `mysite/users/serializers.py` - NEW PublicUserSerializer (or update existing file)

### Backend Files - Modify (Security Hardening)
1. `mysite/auth/views.py` - Update EmailVerificationConfirmView with:
   - Rate limiting decorator (10/15min)
   - CSRF protection decorator
   - Secure IP detection (ipware library)
   - Generic error messages
   - Comprehensive audit logging
   - SameSite=Strict cookies
2. `mysite/auth/views.py` - Update SignupView response to include email_verified (lines 69-142)
3. `mysite/auth/views.py` - Add permission_classes override for ResendVerificationEmailView
4. `mysite/users/views/onboarding.py` - Add IsEmailVerified permission class
5. `mysite/users/views/password.py` - Add token invalidation on password change
6. `mysite/config/settings/base.py` - Add:
   - IsEmailVerified to DEFAULT_PERMISSION_CLASSES (CRITICAL)
   - Security headers (CSP, HSTS, X-Frame-Options)
   - Cookie security settings (SameSite=Strict)

### Backend Files - No Changes Needed
1. ✅ `mysite/auth/services/google_oauth_service.py` - OAuth already sets email_verified=True (lines 391, 368, 471)
2. ✅ `mysite/auth/views_google_oauth.py` - OAuth callback already handles verification

### Frontend Files - Create New (Security Hardening)
1. `web/src/routes/verify-email-required.tsx` - NEW blocking verification page (no polling)
2. `web/src/routes/_authenticated.tsx` - NEW layout route with email verification guard (CRITICAL)
3. `web/src/features/auth/guards/requireEmailVerified.ts` - NEW guard for email verification
4. `web/src/features/auth/schemas/verification.schema.ts` - NEW Zod schemas for runtime validation
5. `web/src/features/auth/hooks/useVerifyEmailConfirm.ts` - UPDATE with Zod validation

### Frontend Files - Modify (Security Hardening)
1. `web/src/lib/api/axios-instance.ts` - ADD security-hardened interceptor:
   - Intercepts 403 with `email_verification_required` error
   - Redirect loop prevention (checks current path)
   - CSRF token injection
   - Proper error handling
   - Shows toast notification

### Frontend Files - Modify & Clean
1. `web/src/features/auth/components/SignupCard.tsx`
   - ✏️ Update redirect logic to `/verify-email-required`

2. `web/src/features/auth/components/EmailVerificationHandler.tsx`
   - ✏️ Add auto-login token handling
   - ✏️ Update redirect to `/circles/onboarding`
   - 🧹 Remove old success page logic

3. `web/src/routes/circles/onboarding.tsx`
   - ✏️ Add `requireEmailVerified` guard

4. `web/src/route-views/circles/components/CircleOnboardingContent.tsx`
   - 🧹 **REMOVE** entire email verification UI section
   - 🧹 **REMOVE** resend/refresh buttons
   - 🧹 **REMOVE** step indicator if present

5. `web/src/features/circles/hooks/useCircleOnboardingController.ts`
   - 🧹 **REMOVE** `canSubmit = status.email_verified` logic
   - 🧹 **REMOVE** `handleResend` function
   - 🧹 **REMOVE** `handleRefresh` function
   - 🧹 **REMOVE** verification-related state

6. `web/src/features/profile/components/ProfileGeneralSettingsCard.tsx`
   - 🧹 **REMOVE** email verification status display
   - 🧹 **REMOVE** "Email verified"/"Email not verified" badges
   - 🧹 **REMOVE** resend/refresh buttons
   - ✏️ Keep email display only (read-only)

7. `web/src/features/auth/types/auth.types.ts`
   - ✏️ Add auto-login fields to verification response type
   - 🧹 Remove unused verification types if any

### Files to Review for Cleanup
- `web/src/features/auth/hooks/emailVerificationHooks.ts` - Keep resend hook (used in new page)
- `web/src/features/circles/hooks/useCircleOnboarding.ts` - Check if email fields needed
- Any CSS files with verification-specific styling
- Any test files for old verification UI

### Legend
- ✏️ Modify/Update
- 🧹 Remove/Clean up
- ✅ Create new

---

## Cleanup Commands (Phase 6 Helper Scripts)

Use these commands to find old code that needs cleanup:

### Search for Verification UI Code
```bash
# Find email verification UI in onboarding
grep -n "email_verified" web/src/route-views/circles/components/CircleOnboardingContent.tsx

# Find verification UI in settings
grep -n "email_verified\|Resend\|Refresh" web/src/features/profile/components/ProfileGeneralSettingsCard.tsx

# Find all verification UI references
grep -rn "email_verified" web/src/route-views/ web/src/features/profile/

# Find resend/refresh button handlers
grep -rn "handleResend\|handleRefresh" web/src/features/circles/
```

### Search for Old Comments & TODOs
```bash
# Find verification-related TODOs
grep -rn "TODO.*verif\|FIXME.*verif" web/src/

# Find old comments about verification flow
grep -rn "// .*verification" web/src/
```

### Find Unused Imports After Cleanup
```bash
# Check for unused imports in onboarding
# (Run linter/build after removing code)
npm run lint web/src/features/circles/
npm run lint web/src/route-views/circles/

# TypeScript unused exports check
npm run build -- --noEmit
```

### Verify Cleanup is Complete
```bash
# Search for any remaining "Step 1 of 2" references
grep -rn "Step 1 of 2\|Step 2 of 2" web/src/

# Search for verification button text
grep -rn "Resend.*verification\|Refresh.*status" web/src/

# Find all canSubmit logic related to email verification
grep -rn "canSubmit.*email_verified" web/src/
```

---

## Internationalization & Copy Requirements

**Why**: The redesign adds blocking screens, new error payloads, and fresh toasts. Every user-facing string must be translated to keep parity with existing English/Spanish support.

### Backend String Wrapping
- `mysite/auth/views.py` – wrap success/error messages from `EmailVerificationConfirmView` in `gettext_lazy as _`.
- `mysite/auth/permissions.py` – ensure the `IsEmailVerified` message uses `_()` so API consumers receive localized errors.
- `mysite/auth/services/email_verification.py` – raise `EmailVerificationError` with localized text for duplicate/inactive cases.

**Spanish `django.po` entries** (append if missing):
```po
msgid "Email verified successfully."
msgstr "Correo electrónico verificado exitosamente."

msgid "Email verification failed. Please try again."
msgstr "Falló la verificación del correo. Inténtalo de nuevo."

msgid "Email verification required to access this resource."
msgstr "Se requiere verificación de correo para acceder a este recurso."

msgid "Email already verified"
msgstr "Correo electrónico ya verificado"

msgid "Cannot verify inactive user account"
msgstr "No se puede verificar cuenta de usuario inactiva"
```

**Commands**:
```bash
django-admin makemessages -l es
django-admin compilemessages
```

### Frontend Translation Keys
Add new namespaces to `web/src/i18n/locales/en.json` (mirror in `es.json`):
```json
{
  "auth": {
    "verify_email_required": {
      "title": "Verify Your Email",
      "message": "We sent a verification email to <strong>{{email}}</strong>",
      "instruction": "Click the link in the email to continue",
      "resend_button": "Resend verification email",
      "resend_sending": "Sending...",
      "logout_link": "Logout"
    },
    "email_verification": {
      "verifying": "Verifying your email...",
      "success": "Email verified successfully!",
      "error": "Email verification failed",
      "redirect_message": "Please verify your email to continue"
    }
  }
}
```

Use these keys in:
- `web/src/routes/verify-email-required.tsx`
- `web/src/features/auth/components/EmailVerificationHandler.tsx`
- `web/src/lib/api/axios-instance.ts` (toast + redirect when `error === 'email_verification_required'`).

### i18n Testing Checklist
- [ ] English + Spanish render `/verify-email-required` with interpolated email and resend states.
- [ ] `EmailVerificationHandler` displays localized loading copy and toast messages.
- [ ] Axios interceptor shows localized redirect toast before navigation.
- [ ] `django-admin compilemessages` succeeds with no missing msgids.
- [ ] Frontend tests cover both locales (snapshot/RTL as needed).

---

## Environment & Security Configuration

**Goal**: Keep verification ergonomic locally while hardening Stage/Prod (cookies, TTL, rate limiting).

### Settings Matrix
| Setting | Local | Staging | Production |
|---------|-------|---------|------------|
| `EMAIL_VERIFICATION_TOKEN_TTL_HOURS` | 48 | 48 | 24 |
| `SESSION_COOKIE_SECURE` | `False` | `True` | `True` |
| `SESSION_COOKIE_SAMESITE` | `'Lax'` | `'Strict'` | `'Strict'` |
| `RATELIMIT_ENABLE` | `False` | `True` | `True` |

### Django Configuration Updates
1. `mysite/config/settings/base.py`
   ```python
   EMAIL_VERIFICATION_TOKEN_TTL_HOURS = _env_int('EMAIL_VERIFICATION_TOKEN_TTL_HOURS', default=48)
   ```
2. `mysite/config/settings/staging.py`
   ```python
   SESSION_COOKIE_SAMESITE = 'Strict'
   CSRF_COOKIE_SAMESITE = 'Strict'
   EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 48
   ```
3. `mysite/config/settings/production.py`
   ```python
   SESSION_COOKIE_SAMESITE = 'Strict'
   CSRF_COOKIE_SAMESITE = 'Strict'
   EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
   ```
4. `mysite/auth/services/token_service.py`
   ```python
   from django.conf import settings

   TOKEN_TTL_HOURS = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_TTL_HOURS', 48)
   # cache.set(..., timeout=60 * 60 * TOKEN_TTL_HOURS)
   ```
5. `mysite/auth/views.py` – use the environment-aware cookie snippet shown earlier (`domain` only when configured).

### Environment Variables
```
# .env.local
EMAIL_VERIFICATION_TOKEN_TTL_HOURS=48

# .env.staging
EMAIL_VERIFICATION_TOKEN_TTL_HOURS=48

# .env.production
EMAIL_VERIFICATION_TOKEN_TTL_HOURS=24
```

### Env Testing Checklist
- [ ] Local tokens remain valid for 48h; production overrides to 24h.
- [ ] Refresh cookies show `SameSite=Strict` + `Secure` in staging/production responses.
- [ ] Rate limiting toggles according to environment flag.
- [ ] QA validates auto-login cookies respect `SESSION_COOKIE_DOMAIN` only when explicitly set.

---

## Consolidated Delivery Checklist

### Backend
- [ ] EmailVerificationService + PublicUserSerializer merged.
- [ ] Global `IsEmailVerified` permission enforced with explicit overrides.
- [ ] i18n strings wrapped; `django.po` updated and compiled.
- [ ] Token TTL + cookie settings sourced from environment variables.

### Frontend
- [ ] `/verify-email-required` route localized and tested.
- [ ] Axios interceptors handle `email_verification_required` with toast + redirect.
- [ ] Signup routing branches on `user.email_verified`.

### Operations & QA
- [ ] End-to-end tests confirm blocking page for unverified accounts.
- [ ] Security review signs off on cookie scope + audit logging.
- [ ] Smoke tests executed for English + Spanish locales.

---

## Next Steps

1. ✅ Review this planning document for completeness and accuracy
2. ✅ Address any questions or clarifications needed
3. ✅ Document approval - Ready for implementation
4. 🔄 Begin implementation:
   - **Phase 1**: Backend Changes (auto-login, OAuth exemption)
   - **Phase 2**: Frontend Routing (new verify-required page)
   - **Phase 3**: Component Updates (remove old UI)
   - **Phase 4**: Guards & Middleware (email verification guard)
   - **Phase 5**: Type Updates (auto-login response types)
   - **Phase 6**: 🧹 **Cleanup Old Code** (remove all old verification flow)
5. Test each phase thoroughly before moving to next
6. Run cleanup commands to verify all old code removed
7. Conduct end-to-end testing of complete flow
8. Manual QA testing with different scenarios
9. Deploy with monitoring

---

**Document Version**: 6.0
**Last Updated**: 2025-10-24
**Status**: ⚠️ **SECURITY REVIEW REQUIRED** - Critical security issues identified, must fix before production
**Security Review**: 🔴 **CRITICAL ISSUES FOUND** - 20 security concerns documented (6 critical, 6 high, 8 moderate)
**Architecture Review**: ✅ Complete - All 6 phases reviewed and improved
**Global Protection**: ✅ CRITICAL - Unverified users blocked from ALL app pages/APIs
**Redirect UX**: ✅ NEW - Backend returns redirect info, frontend intercepts and redirects (no error UI)
**Defense in Depth**: ✅ Frontend layout guard + Backend permission + API interceptor
**OAuth Integration**: ✅ ALREADY IMPLEMENTED - No changes needed (google_oauth_service.py)
**Admin Verification**: ✅ Admin accounts also require email verification
**Rate Limiting**: ⚠️ **INCOMPLETE** - Missing on verification confirm endpoint (CRITICAL FIX REQUIRED)
**Type Safety**: ✅ Enhanced with required fields and TSDoc comments
**Cleanup Phase**: ✅ Comprehensive cleanup plan with validation tasks
**No Migration Needed**: ✅ App not yet deployed - can make breaking changes
**Email Immutability**: ✅ Users cannot change email (no re-verification logic needed)
**No Polling**: ✅ Removed auto-polling (verification link handles auto-login directly)
