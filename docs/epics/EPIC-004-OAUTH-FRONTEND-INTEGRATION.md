# Epic 4: Google OAuth Frontend Integration

**Epic ID**: OAUTH-004  
**Status**: Blocked (depends on OAUTH-002, OAUTH-003)  
**Priority**: P0 - Critical Path  
**Sprint**: Sprint 2, Week 1-2  
**Estimated Effort**: 8 story points  
**Dependencies**: OAUTH-002 (API), OAUTH-003 (Security)  
**Related ADR**: [ADR-010: Google OAuth Integration](../architecture/adr/ADR-010-GOOGLE-OAUTH-INTEGRATION.md)

---

## Epic Goal

Build React frontend components and flows for Google OAuth, including "Sign in with Google" buttons, OAuth callback handling, account linking UI, and comprehensive error handling. This epic delivers the user-facing OAuth experience.

---

## Business Value

- Users can sign up/login with one click
- Reduces signup friction from 3 steps to 1 click
- Improves conversion rates (target: 15-20% improvement)
- Modern, familiar authentication UX

---

## User Stories

### Story 4.1: Google OAuth Button Component
**As a** frontend developer  
**I want** a reusable "Sign in with Google" button  
**So that** OAuth can be used across login/signup pages

**Acceptance Criteria:**
1. `GoogleOAuthButton` component created
2. Follows Google branding guidelines
3. Shows loading state during OAuth flow
4. Handles click to initiate OAuth
5. Accessible (ARIA labels, keyboard navigation)
6. Works on mobile and desktop

**Technical Notes:**
```typescript
// features/auth/oauth/GoogleOAuthButton.tsx
import { useState } from 'react';
import { useGoogleOAuth } from './useGoogleOAuth';
import { Button } from '@/components/ui/button';

interface GoogleOAuthButtonProps {
  mode: 'signup' | 'login' | 'link';
  onSuccess?: (user: User) => void;
  onError?: (error: Error) => void;
  className?: string;
}

export function GoogleOAuthButton({ 
  mode, 
  onSuccess, 
  onError,
  className 
}: GoogleOAuthButtonProps) {
  const { initiateOAuth, isLoading } = useGoogleOAuth();
  
  const handleClick = async () => {
    try {
      await initiateOAuth();
    } catch (error) {
      onError?.(error);
    }
  };
  
  return (
    <Button
      onClick={handleClick}
      disabled={isLoading}
      className={cn('google-oauth-btn', className)}
      aria-label={`Sign ${mode === 'signup' ? 'up' : 'in'} with Google`}
    >
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <GoogleIcon />
          <span>
            {mode === 'signup' ? 'Sign up' : mode === 'login' ? 'Sign in' : 'Link'} with Google
          </span>
        </>
      )}
    </Button>
  );
}
```

**Google Branding Requirements:**
- Use official Google logo SVG
- Follow color scheme: #4285F4 (Google blue)
- Minimum button size: 44x44px (touch target)
- Clear "Sign in with Google" text

**Definition of Done:**
- [ ] Component created and styled
- [ ] Follows Google branding guidelines
- [ ] Accessible (WCAG 2.1 AA)
- [ ] Loading states implemented
- [ ] Works on mobile/desktop
- [ ] Unit tests written
- [ ] Storybook story created

---

### Story 4.2: OAuth Hook (useGoogleOAuth)
**As a** frontend developer  
**I want** a React hook for OAuth logic  
**So that** OAuth state management is reusable

**Acceptance Criteria:**
1. `useGoogleOAuth` hook created
2. Handles OAuth initiation (calls `/api/auth/google/initiate/`)
3. Redirects to Google OAuth URL
4. Handles callback processing
5. Manages loading and error states
6. Returns user data and tokens on success

**Technical Notes:**
```typescript
// features/auth/oauth/useGoogleOAuth.ts
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { oauthApi } from '@/lib/api/oauth';
import { useNavigate } from '@tanstack/react-router';

export function useGoogleOAuth() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  
  const initiateMutation = useMutation({
    mutationFn: () => oauthApi.initiate({
      redirect_uri: window.location.origin + '/auth/google/callback'
    }),
    onSuccess: (data) => {
      // Store state in sessionStorage
      sessionStorage.setItem('oauth_state', data.state);
      // Redirect to Google
      window.location.href = data.google_oauth_url;
    },
    onError: (error) => {
      setIsLoading(false);
      handleOAuthError(error);
    }
  });
  
  const callbackMutation = useMutation({
    mutationFn: (params: { code: string; state: string }) =>
      oauthApi.callback(params),
    onSuccess: (data) => {
      // Store tokens
      authStore.setState({ 
        accessToken: data.tokens.access,
        user: data.user 
      });
      // Navigate to dashboard
      navigate({ to: '/dashboard' });
    },
    onError: handleOAuthError
  });
  
  const initiateOAuth = async () => {
    setIsLoading(true);
    await initiateMutation.mutateAsync();
  };
  
  const handleCallback = async (code: string, state: string) => {
    setIsLoading(true);
    await callbackMutation.mutateAsync({ code, state });
  };
  
  return {
    initiateOAuth,
    handleCallback,
    isLoading,
    error: initiateMutation.error || callbackMutation.error
  };
}
```

**Definition of Done:**
- [ ] Hook created and tested
- [ ] Handles initiate and callback
- [ ] State management with TanStack Store
- [ ] Error handling comprehensive
- [ ] Unit tests written
- [ ] TypeScript types defined

---

### Story 4.3: OAuth Callback Route
**As a** user  
**I want** the OAuth callback to complete automatically  
**So that** I'm logged in after approving Google

**Route:** `/auth/google/callback`

**Acceptance Criteria:**
1. Route handles OAuth callback from Google
2. Extracts code and state from URL parameters
3. Validates state matches stored state
4. Calls backend callback endpoint
5. Shows loading indicator during processing
6. Redirects to dashboard on success
7. Shows clear error message on failure

**Technical Notes:**
```typescript
// routes/auth/google-callback.tsx
import { createFileRoute } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useGoogleOAuth } from '@/features/auth/useGoogleOAuth';
import { Spinner } from '@/components/ui/spinner';

export const Route = createFileRoute('/auth/google/callback')({
  component: GoogleCallbackPage,
});

function GoogleCallbackPage() {
  const searchParams = Route.useSearch();
  const { handleCallback, isLoading, error } = useGoogleOAuth();
  
  useEffect(() => {
    const code = searchParams.code;
    const state = searchParams.state;
    const storedState = sessionStorage.getItem('oauth_state');
    
    if (!code || !state) {
      toast.error('Invalid OAuth callback');
      navigate({ to: '/login' });
      return;
    }
    
    if (state !== storedState) {
      toast.error('OAuth state mismatch. Please try again.');
      navigate({ to: '/login' });
      return;
    }
    
    // Process callback
    handleCallback(code, state);
    
    // Clean up
    sessionStorage.removeItem('oauth_state');
  }, []);
  
  if (error) {
    return (
      <div className="oauth-error">
        <h2>Authentication Failed</h2>
        <p>{getErrorMessage(error)}</p>
        <Button onClick={() => navigate({ to: '/login' })}>
          Back to Login
        </Button>
      </div>
    );
  }
  
  return (
    <div className="oauth-loading">
      <Spinner size="large" />
      <p>Completing sign-in with Google...</p>
    </div>
  );
}
```

**Definition of Done:**
- [ ] Route created and functional
- [ ] URL parameter extraction works
- [ ] State validation implemented
- [ ] Loading state shown
- [ ] Error handling comprehensive
- [ ] Redirects work correctly
- [ ] E2E test passes

---

### Story 4.4: OAuth Error Handling
**As a** user  
**I want** clear error messages when OAuth fails  
**So that** I know what went wrong and what to do

**Acceptance Criteria:**
1. All OAuth error codes have user-friendly messages
2. Error messages provide actionable guidance
3. Errors display in toast notifications
4. Critical errors (unverified account) show modal dialog
5. Error reporting to logging service

**Error Message Mapping:**
```typescript
// features/auth/oauth/oauth-utils.ts
export const OAUTH_ERROR_MESSAGES = {
  'UNVERIFIED_ACCOUNT_EXISTS': {
    title: 'Email Verification Required',
    message: 'An account with this email exists but is not verified. Please check your email for the verification link.',
    action: 'Resend Verification Email',
    severity: 'warning',
  },
  'GOOGLE_API_ERROR': {
    title: 'Connection Error',
    message: 'Unable to connect to Google. Please try again in a moment.',
    action: 'Retry',
    severity: 'error',
  },
  'INVALID_STATE_TOKEN': {
    title: 'Session Expired',
    message: 'Your sign-in session has expired. Please try again.',
    action: 'Try Again',
    severity: 'info',
  },
  'RATE_LIMIT_EXCEEDED': {
    title: 'Too Many Attempts',
    message: 'You\'ve tried too many times. Please wait 15 minutes before trying again.',
    action: null,
    severity: 'error',
  },
  'GOOGLE_ACCOUNT_ALREADY_LINKED': {
    title: 'Already Linked',
    message: 'This Google account is already linked to another user.',
    action: 'Contact Support',
    severity: 'error',
  },
  'INVALID_REDIRECT_URI': {
    title: 'Configuration Error',
    message: 'There was a problem with the sign-in configuration. Please contact support.',
    action: 'Contact Support',
    severity: 'error',
  },
} as const;

export function getOAuthErrorMessage(error: ApiError) {
  const errorCode = error.error?.code || 'UNKNOWN_ERROR';
  const errorInfo = OAUTH_ERROR_MESSAGES[errorCode];
  
  if (!errorInfo) {
    return {
      title: 'Sign-in Failed',
      message: 'An unexpected error occurred. Please try again.',
      action: 'Try Again',
      severity: 'error',
    };
  }
  
  return errorInfo;
}
```

**Definition of Done:**
- [ ] All error codes mapped
- [ ] Messages are user-friendly
- [ ] Toasts display correctly
- [ ] Modal for critical errors
- [ ] Error logging implemented
- [ ] Tested with all error scenarios

---

### Story 4.5: Login/Signup Page Integration
**As a** user  
**I want** to see "Sign in with Google" on login/signup pages  
**So that** I can use Google authentication

**Acceptance Criteria:**
1. "Sign in with Google" button on login page
2. "Sign up with Google" button on signup page
3. "OR" divider between Google and manual auth
4. Buttons styled consistently with brand
5. Mobile-responsive layout
6. Loading states during OAuth flow

**Design:**
```
┌─────────────────────────────────────┐
│         Sign in to Tinybeans        │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────────┐ │
│  │    Sign in with Google        │ │
│  └───────────────────────────────┘ │
│                                     │
│  ────────────  OR  ──────────────  │
│                                     │
│  Email: [_________________]         │
│  Password: [_________________]      │
│                                     │
│  [    Sign In    ]                  │
│                                     │
│  Forgot password? | Sign up         │
└─────────────────────────────────────┘
```

**Technical Notes:**
```tsx
// routes/login.tsx
import { GoogleOAuthButton } from '@/features/auth/GoogleOAuthButton';

function LoginPage() {
  return (
    <div className="auth-container">
      <h1>Sign in to Tinybeans</h1>
      
      <GoogleOAuthButton 
        mode="login"
        onSuccess={(user) => navigate({ to: '/dashboard' })}
        onError={(error) => toast.error(getOAuthErrorMessage(error))}
      />
      
      <div className="auth-divider">
        <span>OR</span>
      </div>
      
      <LoginForm />
    </div>
  );
}
```

**Definition of Done:**
- [ ] Button integrated on login page
- [ ] Button integrated on signup page
- [ ] Layout is mobile-responsive
- [ ] Styling matches design system
- [ ] OAuth flow works end-to-end
- [ ] Visual regression tests pass

---

### Story 4.6: Account Linking UI in Settings
**As an** authenticated user  
**I want** to link/unlink my Google account in settings  
**So that** I can manage my authentication methods

**Acceptance Criteria:**
1. Settings page shows OAuth connection status
2. "Link Google Account" button if not linked
3. "Unlink Google Account" button if linked
4. Password required to unlink (security)
5. Shows auth_provider status (manual/google/hybrid)
6. Success/error messages for link/unlink actions

**Design:**
```
┌─────────────────────────────────────┐
│     Authentication Settings         │
├─────────────────────────────────────┤
│                                     │
│  Primary Method: Manual + Google    │
│                                     │
│  ┌─ Google Account ────────────┐   │
│  │  ✓ Connected                │   │
│  │  user@gmail.com            │   │
│  │  Linked: Jan 12, 2025      │   │
│  │                             │   │
│  │  [  Unlink Google Account  ]│   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌─ Password ──────────────────┐   │
│  │  ✓ Set                      │   │
│  │  [  Change Password  ]      │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Technical Notes:**
```tsx
// modules/settings/AuthenticationSettings.tsx
export function AuthenticationSettings() {
  const { user } = useStore(authStore);
  const linkMutation = useMutation({ mutationFn: oauthApi.link });
  const unlinkMutation = useMutation({ mutationFn: oauthApi.unlink });
  
  const handleLink = () => {
    // Initiate OAuth for linking
    useGoogleOAuth().initiateOAuth();
  };
  
  const handleUnlink = () => {
    // Show password confirmation dialog
    showConfirmDialog({
      title: 'Unlink Google Account',
      message: 'Enter your password to unlink your Google account',
      requirePassword: true,
      onConfirm: async (password) => {
        await unlinkMutation.mutateAsync({ password });
        toast.success('Google account unlinked');
      }
    });
  };
  
  return (
    <div className="auth-settings">
      {user.google_id ? (
        <GoogleAccountConnected 
          email={user.google_email}
          linkedAt={user.google_linked_at}
          onUnlink={handleUnlink}
        />
      ) : (
        <GoogleAccountNotConnected onLink={handleLink} />
      )}
    </div>
  );
}
```

**Definition of Done:**
- [ ] Settings page UI created
- [ ] Shows correct connection status
- [ ] Link/unlink functionality works
- [ ] Password confirmation dialog
- [ ] Success/error handling
- [ ] Visual design matches mockups

---

## Epic Acceptance Criteria

This epic is complete when:
- [ ] All 6 stories completed
- [ ] "Sign in with Google" works on login/signup pages
- [ ] OAuth callback processes correctly
- [ ] Errors display user-friendly messages
- [ ] Account linking in settings works
- [ ] Mobile and desktop layouts tested
- [ ] E2E tests pass for full OAuth flow

---

## Testing Requirements

### Unit Tests
- GoogleOAuthButton component
- useGoogleOAuth hook
- OAuth error message mapping
- State validation logic

### Integration Tests
- Full OAuth flow (button click → callback → logged in)
- Error handling scenarios
- Account linking/unlinking

### E2E Tests (Playwright/Cypress)
- User clicks "Sign in with Google"
- Redirects to Google (mock)
- Returns to callback
- User is logged in
- Dashboard loads

### Visual Regression Tests
- OAuth button styles
- Loading states
- Error displays
- Mobile layouts

---

## Accessibility Requirements

- [ ] Keyboard navigation works (Tab through OAuth button)
- [ ] Screen reader announces OAuth button correctly
- [ ] Error messages announced to screen readers
- [ ] Focus management during OAuth flow
- [ ] Color contrast meets WCAG 2.1 AA
- [ ] Touch targets ≥ 44x44px

---

## Documentation Updates

- [ ] Component API documentation (Storybook)
- [ ] Developer integration guide
- [ ] User help article "How to sign in with Google"
- [ ] Screenshots for user documentation

---

## Dependencies & Blockers

**Upstream Dependencies:**
- OAUTH-002: API Implementation (API endpoints must exist)
- OAUTH-003: Security Hardening (security must be validated)

**Blocks:**
- Production launch (user-facing feature)
- User onboarding improvements

---

## Success Metrics

- OAuth flow completes in < 5 seconds (p95)
- < 5% user error rate during OAuth
- Mobile and desktop layouts work perfectly
- Accessibility score 100 (Lighthouse)

---

**Epic Owner**: Frontend Team Lead  
**Stakeholders**: Frontend Developers, UX Designer, QA  
**Target Completion**: End of Sprint 2, Week 2

