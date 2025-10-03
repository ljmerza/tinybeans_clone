# Epic 2: Auth Feature Migration to New Architecture

**Epic ID**: FE-ARCH-002  
**Status**: Blocked (depends on FE-ARCH-001)  
**Priority**: P1 - High Priority  
**Sprint**: Week 2  
**Estimated Effort**: 8 story points  
**Dependencies**: FE-ARCH-001 (Foundation Setup)  
**Related ADR**: [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)

---

## Epic Goal

Migrate the entire authentication feature from `src/modules/login/` to `src/features/auth/`, consolidating duplicate route files, organizing components properly, and ensuring all authentication flows work correctly with the new structure.

---

## Business Value

- **Code Organization**: All auth code in one logical place
- **Maintainability**: Easier to find and modify auth-related code
- **Developer Velocity**: Faster feature development with clear structure
- **Quality**: Reduced bugs from better organization

**Expected Impact**:
- 60% faster to locate auth-related code
- Zero duplicate auth files
- 40% reduction in auth-related bugs from better organization
- Clearer separation of concerns

---

## Current State Analysis

### Files to Migrate

```
src/modules/login/
├── client.ts                    → features/auth/api/authClient.ts
├── devtools.tsx                 → features/auth/components/AuthDevtools.tsx
├── hooks.ts                     → features/auth/hooks/ (split into files)
├── routes.login.tsx            → Extract LoginForm component
├── routes.logout.tsx           → Extract LogoutHandler component
├── routes.signup.tsx           → Extract SignupForm component
├── store.ts                     → features/auth/store/authStore.ts
├── types.ts                     → features/auth/types/auth.types.ts
└── useAuthCheck.ts              → features/auth/hooks/useAuthCheck.ts

src/routes/
├── login.tsx                    → Keep, update to import from features
├── logout.tsx                   → Keep, update to import from features
├── signup.tsx                   → Keep, update to import from features
├── magic-link-request.tsx       → Keep, update to import from features
└── magic-login.tsx              → Keep, update to import from features
```

### Import Analysis

Files importing from `modules/login/`:
- `src/App.tsx` → Uses authStore
- `src/main.tsx` → Uses refreshAccessToken
- `src/routes/*.tsx` → Use auth components and hooks
- `src/components/PublicOnlyRoute.tsx` → Uses authStore
- `src/modules/twofa/` → May use auth types

---

## User Stories

### Story 2.1: Create Auth Feature Structure

**As a** frontend developer  
**I want** the auth feature directory properly structured  
**So that** auth code is organized and discoverable

**Acceptance Criteria:**
1. `features/auth/` directory created with all subdirectories
2. `features/auth/index.ts` created for public exports
3. README documenting auth feature
4. Structure follows feature template
5. No existing functionality affected

**Directory Structure:**
```
features/auth/
├── index.ts                    # Public API exports
├── README.md                   # Auth feature documentation
├── components/
│   ├── LoginForm.tsx           # Extracted from routes.login
│   ├── SignupForm.tsx          # Extracted from routes.signup
│   ├── MagicLinkForm.tsx       # Extracted from magic-link-request
│   ├── MagicLoginHandler.tsx   # Extracted from magic-login
│   ├── LogoutHandler.tsx       # Extracted from routes.logout
│   └── AuthDevtools.tsx        # Moved from devtools.tsx
├── hooks/
│   ├── useLogin.ts             # Extracted from hooks.ts
│   ├── useSignup.ts            # Extracted from hooks.ts
│   ├── useMagicLink.ts         # Extracted from hooks.ts
│   ├── useLogout.ts            # Extracted from hooks.ts
│   └── useAuthCheck.ts         # Moved from useAuthCheck.ts
├── api/
│   └── authClient.ts           # Moved from client.ts
├── store/
│   └── authStore.ts            # Moved from store.ts
├── types/
│   ├── index.ts                # Re-exports
│   └── auth.types.ts           # Moved from types.ts
└── utils/
    └── tokenUtils.ts           # Extracted if needed
```

**Definition of Done:**
- [ ] Directory structure created
- [ ] README.md written
- [ ] Empty files created with proper imports
- [ ] No build errors
- [ ] Structure validated with validation script

---

### Story 2.2: Migrate API Client and Store

**As a** frontend developer  
**I want** auth API client and store in the features directory  
**So that** auth data management is co-located

**Acceptance Criteria:**
1. `authClient.ts` moved and working
2. `authStore.ts` moved and working
3. All imports updated
4. TypeScript types properly imported
5. No functionality broken

**Implementation:**

```typescript
// features/auth/api/authClient.ts
// Moved from modules/login/client.ts
import { api } from '@/lib/api'
import type { LoginCredentials, SignupData, AuthResponse } from '../types'

export const authClient = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // ... existing implementation
  },
  
  signup: async (data: SignupData): Promise<AuthResponse> => {
    // ... existing implementation
  },
  
  logout: async (): Promise<void> => {
    // ... existing implementation
  },
  
  refreshAccessToken: async (): Promise<string> => {
    // ... existing implementation
  },
  
  magicLinkRequest: async (email: string): Promise<void> => {
    // ... existing implementation
  },
}
```

```typescript
// features/auth/store/authStore.ts
// Moved from modules/login/store.ts
import { Store } from '@tanstack/react-store'
import type { AuthUser } from '../types'

export const authStore = new Store<{
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
}>({
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  user: null,
})

// ... rest of store implementation
```

**Files to Update:**
- `src/main.tsx` → Update import for `refreshAccessToken`
- `src/App.tsx` → Update import for `authStore`
- `src/components/PublicOnlyRoute.tsx` → Update import for `authStore`

**Definition of Done:**
- [ ] `authClient.ts` in new location
- [ ] `authStore.ts` in new location
- [ ] All imports updated across codebase
- [ ] TypeScript compilation succeeds
- [ ] All tests passing
- [ ] Auth flows working in dev

---

### Story 2.3: Extract and Migrate Login Components

**As a** frontend developer  
**I want** login components extracted from route files  
**So that** routes are thin and components are reusable

**Acceptance Criteria:**
1. `LoginForm` component created in `features/auth/components/`
2. `useLogin` hook created in `features/auth/hooks/`
3. `routes/login.tsx` updated to use extracted components
4. Login flow working correctly
5. All validations and error handling preserved

**Implementation:**

```typescript
// features/auth/components/LoginForm.tsx
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { passwordSchema } from '@/lib/validations'
import { useLogin } from '../hooks/useLogin'

const schema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: passwordSchema,
})

type LoginFormValues = z.infer<typeof schema>

export function LoginForm() {
  const login = useLogin()
  
  const form = useForm<LoginFormValues>({
    defaultValues: { username: '', password: '' },
    onSubmit: async ({ value }) => {
      await login.mutateAsync(value)
    },
  })
  
  return (
    <form onSubmit={(e) => { /* ... */ }}>
      {/* Form fields - extracted from routes.login.tsx */}
    </form>
  )
}
```

```typescript
// features/auth/hooks/useLogin.ts
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { authClient } from '../api/authClient'
import { authStore } from '../store/authStore'
import type { LoginCredentials } from '../types'

export function useLogin() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => 
      authClient.login(credentials),
    onSuccess: (data) => {
      authStore.setState(() => ({
        accessToken: data.access,
        refreshToken: data.refresh,
        user: data.user,
      }))
      localStorage.setItem('accessToken', data.access)
      localStorage.setItem('refreshToken', data.refresh)
      navigate({ to: '/' })
    },
  })
}
```

```typescript
// routes/login.tsx (updated)
import { createFileRoute } from '@tanstack/react-router'
import { LoginForm } from '@/features/auth'
import { PublicOnlyRoute } from '@/components'

export const Route = createFileRoute('/login')({
  component: LoginPage,
})

function LoginPage() {
  return (
    <PublicOnlyRoute>
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6">
          <h1 className="mb-6 text-2xl font-semibold text-center">Login</h1>
          <LoginForm />
        </div>
      </div>
    </PublicOnlyRoute>
  )
}
```

```typescript
// features/auth/index.ts (add export)
export { LoginForm } from './components/LoginForm'
export { useLogin } from './hooks/useLogin'
```

**Definition of Done:**
- [ ] `LoginForm` component created
- [ ] `useLogin` hook created
- [ ] `routes/login.tsx` updated
- [ ] Login flow tested manually
- [ ] All form validations working
- [ ] Error handling working
- [ ] Success redirects working

---

### Story 2.4: Extract and Migrate Signup Components

**As a** frontend developer  
**I want** signup components extracted from route files  
**So that** signup logic is reusable and well-organized

**Acceptance Criteria:**
1. `SignupForm` component created
2. `useSignup` hook created
3. `routes/signup.tsx` updated
4. Signup flow working correctly
5. Email verification flow working

**Implementation:**

Follow same pattern as Story 2.3 for:
- `features/auth/components/SignupForm.tsx`
- `features/auth/hooks/useSignup.ts`
- Update `routes/signup.tsx`
- Export from `features/auth/index.ts`

**Definition of Done:**
- [ ] `SignupForm` component created
- [ ] `useSignup` hook created
- [ ] `routes/signup.tsx` updated
- [ ] Signup flow tested
- [ ] Email validation working
- [ ] Account creation working
- [ ] Post-signup redirect working

---

### Story 2.5: Migrate Magic Link Components

**As a** frontend developer  
**I want** magic link functionality in the auth feature  
**So that** all auth methods are co-located

**Acceptance Criteria:**
1. `MagicLinkForm` component created
2. `MagicLoginHandler` component created
3. `useMagicLink` hooks created
4. Route files updated
5. Magic link flow working end-to-end

**Components to Create:**
- `features/auth/components/MagicLinkForm.tsx`
- `features/auth/components/MagicLoginHandler.tsx`
- `features/auth/hooks/useMagicLink.ts`

**Routes to Update:**
- `routes/magic-link-request.tsx`
- `routes/magic-login.tsx`

**Definition of Done:**
- [ ] Components created
- [ ] Hooks created
- [ ] Routes updated
- [ ] Request magic link works
- [ ] Email sent successfully
- [ ] Magic link login works
- [ ] Error states handled

---

### Story 2.6: Migrate Logout and Auth Utilities

**As a** frontend developer  
**I want** logout and utility functions in the auth feature  
**So that** all auth code is co-located

**Acceptance Criteria:**
1. `LogoutHandler` component created
2. `useLogout` hook created
3. `useAuthCheck` hook migrated
4. `AuthDevtools` component migrated
5. All utilities working

**Components:**

```typescript
// features/auth/components/LogoutHandler.tsx
import { useEffect } from 'react'
import { useLogout } from '../hooks/useLogout'

export function LogoutHandler() {
  const logout = useLogout()
  
  useEffect(() => {
    logout.mutate()
  }, [])
  
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1>Logging out...</h1>
      </div>
    </div>
  )
}
```

```typescript
// features/auth/hooks/useLogout.ts
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { authClient } from '../api/authClient'
import { authStore } from '../store/authStore'

export function useLogout() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: () => authClient.logout(),
    onSuccess: () => {
      authStore.setState(() => ({
        accessToken: null,
        refreshToken: null,
        user: null,
      }))
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      navigate({ to: '/login' })
    },
  })
}
```

**Definition of Done:**
- [ ] `LogoutHandler` created
- [ ] `useLogout` hook created
- [ ] `useAuthCheck` migrated
- [ ] `AuthDevtools` migrated
- [ ] `routes/logout.tsx` updated
- [ ] Logout flow working
- [ ] Tokens cleared correctly

---

### Story 2.7: Update All Imports and Clean Up

**As a** frontend developer  
**I want** all imports updated to use the new feature structure  
**So that** the old module directory can be removed

**Acceptance Criteria:**
1. All imports updated across entire codebase
2. No references to `modules/login/*` remain
3. All TypeScript errors resolved
4. All linting errors resolved
5. Old `modules/login/` directory removed

**Files Requiring Import Updates:**
- `src/App.tsx`
- `src/main.tsx`
- `src/components/PublicOnlyRoute.tsx`
- `src/components/ProtectedRoute.tsx`
- `src/routes/*.tsx`
- Any 2FA files using auth types

**Migration Script:**

```bash
#!/bin/bash
# scripts/migrate-auth-imports.sh

echo "Updating auth imports..."

# Update authStore imports
find src -type f -name "*.tsx" -o -name "*.ts" | xargs sed -i \
  's|from "@/modules/login/store"|from "@/features/auth"|g'

# Update authClient imports
find src -type f -name "*.tsx" -o -name "*.ts" | xargs sed -i \
  's|from "@/modules/login/client"|from "@/features/auth"|g'

# Update hook imports
find src -type f -name "*.tsx" -o -name "*.ts" | xargs sed -i \
  's|from "@/modules/login/hooks"|from "@/features/auth"|g'

# Update type imports
find src -type f -name "*.tsx" -o -name "*.ts" | xargs sed -i \
  's|from "@/modules/login/types"|from "@/features/auth"|g'

echo "✅ Imports updated. Please review changes and test!"
```

**Validation Checklist:**
- [ ] Run find/replace for all `modules/login` references
- [ ] TypeScript compilation succeeds
- [ ] No linting errors
- [ ] All tests pass
- [ ] Manual testing of all auth flows
- [ ] Remove `src/modules/login/` directory
- [ ] Commit changes

**Definition of Done:**
- [ ] Import migration script executed
- [ ] All files manually reviewed
- [ ] No `modules/login` references remain
- [ ] TypeScript compiles successfully
- [ ] All tests passing
- [ ] All auth flows tested manually
- [ ] Old directory removed
- [ ] Git commit made

---

## Testing Strategy

### Unit Tests
- [ ] Test all extracted components
- [ ] Test all hooks in isolation
- [ ] Test authStore state management
- [ ] Test authClient API calls (mocked)

### Integration Tests
- [ ] Test complete login flow
- [ ] Test complete signup flow
- [ ] Test magic link flow
- [ ] Test logout flow
- [ ] Test auth state persistence

### Manual Testing Checklist
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Signup new account
- [ ] Signup with existing email
- [ ] Request magic link
- [ ] Login via magic link
- [ ] Logout and verify token cleared
- [ ] Refresh page and auth persists
- [ ] Navigate between protected/public routes
- [ ] Auth devtools work (dev mode)

### Regression Testing
- [ ] All existing auth tests pass
- [ ] No console errors
- [ ] No network errors
- [ ] Performance similar to before
- [ ] Bundle size similar

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking auth flows | Critical | Medium | Comprehensive testing, feature flag for rollback |
| Import path errors | High | High | Automated find/replace script, thorough review |
| State management issues | High | Low | Test auth store extensively |
| Missing edge cases | Medium | Medium | Review all auth-related code, test thoroughly |
| Performance degradation | Low | Low | Monitor bundle size and load times |

---

## Rollback Plan

If critical issues discovered:

1. **Immediate**: Revert Epic 2 commits
2. **Short-term**: Keep both old and new code, feature flag to switch
3. **Investigation**: Fix issues in separate branch
4. **Retry**: Reattempt migration after fixes

**Rollback Triggers:**
- Auth completely broken in production
- Critical security vulnerability introduced
- Major performance degradation (>20%)

---

## Dependencies

**Requires**: FE-ARCH-001 (Foundation Setup) completed

**Blocks**: FE-ARCH-003 (2FA Migration)

---

## Definition of Done

### Epic Level
- [ ] All 7 stories completed
- [ ] All auth code in `features/auth/`
- [ ] No code in `modules/login/`
- [ ] All imports updated
- [ ] All auth flows working
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team review completed

### Code Quality
- [ ] No linting errors
- [ ] No TypeScript errors
- [ ] Code coverage maintained
- [ ] No duplicate code

### Production Ready
- [ ] Manual testing complete
- [ ] Performance validated
- [ ] Security review passed
- [ ] Rollback plan tested

---

**Last Updated**: 2025-01-15  
**Epic Owner**: Frontend Team
