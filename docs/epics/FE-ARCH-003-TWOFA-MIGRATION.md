# Epic 3: 2FA Feature Migration to New Architecture

**Epic ID**: FE-ARCH-003  
**Status**: Blocked (depends on FE-ARCH-002)  
**Priority**: P1 - High Priority  
**Sprint**: Week 3  
**Estimated Effort**: 6 story points  
**Dependencies**: FE-ARCH-002 (Auth Migration)  
**Related ADR**: [ADR-011: Frontend File Architecture](../architecture/adr/ADR-011-FRONTEND-FILE-ARCHITECTURE.md)

---

## Epic Goal

Migrate the two-factor authentication feature from `src/modules/twofa/` to `src/features/twofa/`, organizing the complex component hierarchy, consolidating route files, and ensuring all 2FA flows (setup, verification, management) work correctly with the new structure.

---

## Business Value

- **Feature Isolation**: 2FA code clearly separated from auth
- **Maintainability**: Complex 2FA flows easier to understand
- **Reusability**: 2FA components can be composed flexibly
- **Scalability**: Adding new 2FA methods will be clearer

**Expected Impact**:
- 50% faster to locate 2FA-related code
- Easier to add new 2FA methods (SMS, hardware keys)
- Better separation between authentication and 2FA
- Improved testability of 2FA flows

---

## Current State Analysis

### Files to Migrate

```
src/modules/twofa/
├── client.ts                           → features/twofa/api/twofaClient.ts
├── hooks.ts                            → features/twofa/hooks/ (split)
├── index.ts                            → features/twofa/index.ts
├── types.ts                            → features/twofa/types/twofa.types.ts
└── components/
    ├── DisableTwoFactorSection.tsx     → features/twofa/components/
    ├── TwoFactorStatusHeader.tsx       → features/twofa/components/
    ├── TwoFactorEnabledSettings.tsx    → features/twofa/components/
    ├── RecoveryCodeList.tsx            → features/twofa/components/
    ├── RecoveryCodesSection.tsx        → features/twofa/components/
    ├── TrustedDevicesSection.tsx       → features/twofa/components/
    ├── QRCodeDisplay.tsx               → features/twofa/components/
    ├── EmailSetup.tsx                  → features/twofa/components/setup/
    ├── SmsSetup.tsx                    → features/twofa/components/setup/
    └── setup/
        ├── email/                      → features/twofa/components/setup/email/
        ├── sms/                        → features/twofa/components/setup/sms/
        ├── totp/                       → features/twofa/components/setup/totp/
        └── methods/                    → features/twofa/components/methods/

src/routes/2fa/
├── settings.tsx                        → Keep, update imports
├── setup/                              → Keep, update imports
├── verify.tsx                          → Keep, update imports
└── trusted-devices.tsx                 → Keep, update imports
```

### Complexity Assessment

**High Complexity Items:**
- Multi-step setup wizards (email, SMS, TOTP)
- Component nesting 3-4 levels deep
- Shared state between setup steps
- Multiple 2FA method types

**Dependencies:**
- May import auth types from `features/auth`
- Uses shared UI components
- API client similar structure to auth

---

## User Stories

### Story 3.1: Create 2FA Feature Structure

**As a** frontend developer  
**I want** the 2FA feature directory properly structured  
**So that** complex 2FA code is organized and navigable

**Acceptance Criteria:**
1. `features/twofa/` directory created
2. Subdirectories for components, hooks, api, types
3. Component hierarchy preserved
4. README documenting 2FA feature
5. Structure validated

**Directory Structure:**
```
features/twofa/
├── index.ts                           # Public API exports
├── README.md                          # 2FA feature documentation
├── components/
│   ├── setup/                         # Setup wizards
│   │   ├── TwoFactorSetup.tsx        # Main setup component
│   │   ├── email/
│   │   │   ├── EmailIntroStep.tsx
│   │   │   ├── EmailVerifyStep.tsx
│   │   │   └── EmailRecoveryStep.tsx
│   │   ├── sms/
│   │   │   ├── SmsIntroStep.tsx
│   │   │   ├── SmsVerifyStep.tsx
│   │   │   └── SmsRecoveryStep.tsx
│   │   ├── totp/
│   │   │   ├── TotpIntroStep.tsx
│   │   │   ├── TotpScanStep.tsx
│   │   │   ├── TotpVerifyStep.tsx
│   │   │   └── TotpRecoveryStep.tsx
│   │   └── MethodSelector.tsx
│   ├── verify/                        # Verification components
│   │   ├── TwoFactorVerify.tsx
│   │   └── MethodVerification.tsx
│   ├── settings/                      # Management components
│   │   ├── TwoFactorSettings.tsx
│   │   ├── TwoFactorStatusHeader.tsx
│   │   ├── TwoFactorEnabledSettings.tsx
│   │   ├── DisableTwoFactorSection.tsx
│   │   ├── RecoveryCodesSection.tsx
│   │   ├── RecoveryCodeList.tsx
│   │   └── TrustedDevicesSection.tsx
│   └── shared/                        # Shared 2FA components
│       └── QRCodeDisplay.tsx
├── hooks/
│   ├── useTwoFactorSetup.ts
│   ├── useTwoFactorVerify.ts
│   ├── useTwoFactorStatus.ts
│   ├── useRecoveryCodes.ts
│   └── useTrustedDevices.ts
├── api/
│   └── twofaClient.ts
├── types/
│   └── twofa.types.ts
└── utils/
    └── qrcode.ts                      # QR code generation utilities
```

**README.md Content:**
```markdown
# 2FA Feature

Two-factor authentication implementation supporting multiple methods:
- TOTP (Time-based One-Time Password)
- SMS verification
- Email verification

## Components

### Setup Flow
Multi-step wizards for each 2FA method located in `components/setup/`

### Verification
Verification components for login flows in `components/verify/`

### Settings
Management and configuration in `components/settings/`

## Public API

Only import from the feature index:
\`\`\`typescript
import { TwoFactorSetup, useTwoFactorSetup } from '@/features/twofa'
\`\`\`

## Adding New 2FA Method

1. Create method directory in `components/setup/{method}/`
2. Implement step components
3. Add to MethodSelector
4. Update types and API client
```

**Definition of Done:**
- [ ] Directory structure created
- [ ] README.md written
- [ ] All subdirectories created
- [ ] Structure validated
- [ ] No build errors

---

### Story 3.2: Migrate 2FA API Client and Types

**As a** frontend developer  
**I want** 2FA API client and types in the feature  
**So that** 2FA data management is co-located

**Acceptance Criteria:**
1. `twofaClient.ts` migrated
2. `twofa.types.ts` migrated
3. Types properly exported
4. API client working
5. TypeScript compilation succeeds

**Implementation:**

```typescript
// features/twofa/api/twofaClient.ts
import { api } from '@/lib/api'
import type {
  TwoFactorMethod,
  TwoFactorSetupResponse,
  TwoFactorVerifyRequest,
  TrustedDevice,
  RecoveryCode,
} from '../types'

export const twofaClient = {
  // Setup endpoints
  setupTotp: async (): Promise<TwoFactorSetupResponse> => {
    const response = await api.post('/api/auth/2fa/totp/setup/')
    return response.data
  },
  
  setupEmail: async (): Promise<TwoFactorSetupResponse> => {
    const response = await api.post('/api/auth/2fa/email/setup/')
    return response.data
  },
  
  setupSms: async (phoneNumber: string): Promise<TwoFactorSetupResponse> => {
    const response = await api.post('/api/auth/2fa/sms/setup/', { phoneNumber })
    return response.data
  },
  
  // Verification endpoints
  verify: async (data: TwoFactorVerifyRequest): Promise<void> => {
    await api.post('/api/auth/2fa/verify/', data)
  },
  
  // Status and management
  getStatus: async (): Promise<{ enabled: boolean; methods: TwoFactorMethod[] }> => {
    const response = await api.get('/api/auth/2fa/status/')
    return response.data
  },
  
  disable: async (): Promise<void> => {
    await api.post('/api/auth/2fa/disable/')
  },
  
  // Recovery codes
  getRecoveryCodes: async (): Promise<RecoveryCode[]> => {
    const response = await api.get('/api/auth/2fa/recovery-codes/')
    return response.data
  },
  
  regenerateRecoveryCodes: async (): Promise<RecoveryCode[]> => {
    const response = await api.post('/api/auth/2fa/recovery-codes/regenerate/')
    return response.data
  },
  
  // Trusted devices
  getTrustedDevices: async (): Promise<TrustedDevice[]> => {
    const response = await api.get('/api/auth/2fa/trusted-devices/')
    return response.data
  },
  
  removeTrustedDevice: async (deviceId: string): Promise<void> => {
    await api.delete(`/api/auth/2fa/trusted-devices/${deviceId}/`)
  },
}
```

```typescript
// features/twofa/types/twofa.types.ts
export type TwoFactorMethod = 'totp' | 'sms' | 'email'

export interface TwoFactorSetupResponse {
  method: TwoFactorMethod
  qrCode?: string  // For TOTP
  secret?: string  // For TOTP
  backupCodes: string[]
}

export interface TwoFactorVerifyRequest {
  method: TwoFactorMethod
  code: string
  trustDevice?: boolean
}

export interface TrustedDevice {
  id: string
  name: string
  lastUsed: string
  createdAt: string
}

export interface RecoveryCode {
  code: string
  used: boolean
}

export interface TwoFactorStatus {
  enabled: boolean
  methods: TwoFactorMethod[]
  hasTrustedDevices: boolean
}
```

**Definition of Done:**
- [ ] API client migrated
- [ ] Types migrated
- [ ] Imports updated
- [ ] TypeScript compiles
- [ ] No runtime errors

---

### Story 3.3: Migrate 2FA Setup Components

**As a** frontend developer  
**I want** 2FA setup components in the feature  
**So that** setup wizards are well-organized

**Acceptance Criteria:**
1. All setup step components migrated
2. Component hierarchy preserved
3. Setup flows working for all methods
4. State management working
5. Navigation between steps working

**Components to Migrate:**

**TOTP Setup (4 steps):**
- `TotpIntroStep.tsx` - Explains TOTP
- `TotpScanStep.tsx` - Shows QR code
- `TotpVerifyStep.tsx` - Verifies code
- `TotpRecoveryStep.tsx` - Shows backup codes

**Email Setup (3 steps):**
- `EmailIntroStep.tsx`
- `EmailVerifyStep.tsx`
- `EmailRecoveryStep.tsx`

**SMS Setup (3 steps):**
- `SmsIntroStep.tsx`
- `SmsVerifyStep.tsx`
- `SmsRecoveryStep.tsx`

**Main Setup Component:**
```typescript
// features/twofa/components/setup/TwoFactorSetup.tsx
import { useState } from 'react'
import { MethodSelector } from './MethodSelector'
import { TotpSetup } from './totp/TotpSetup'
import { EmailSetup } from './email/EmailSetup'
import { SmsSetup } from './sms/SmsSetup'
import type { TwoFactorMethod } from '../../types'

export function TwoFactorSetup() {
  const [selectedMethod, setSelectedMethod] = useState<TwoFactorMethod | null>(null)
  
  if (!selectedMethod) {
    return <MethodSelector onSelect={setSelectedMethod} />
  }
  
  switch (selectedMethod) {
    case 'totp':
      return <TotpSetup onCancel={() => setSelectedMethod(null)} />
    case 'email':
      return <EmailSetup onCancel={() => setSelectedMethod(null)} />
    case 'sms':
      return <SmsSetup onCancel={() => setSelectedMethod(null)} />
  }
}
```

**Definition of Done:**
- [ ] All setup components migrated
- [ ] Component structure preserved
- [ ] TOTP setup working
- [ ] Email setup working
- [ ] SMS setup working
- [ ] Step navigation working
- [ ] All validations working

---

### Story 3.4: Migrate 2FA Verification Components

**As a** frontend developer  
**I want** 2FA verification components in the feature  
**So that** login-time verification is organized

**Acceptance Criteria:**
1. Verification components migrated
2. All 2FA methods can be verified
3. Error handling working
4. Trust device option working
5. Recovery code fallback working

**Components:**
```typescript
// features/twofa/components/verify/TwoFactorVerify.tsx
import { useState } from 'react'
import { useTwoFactorVerify } from '../../hooks/useTwoFactorVerify'
import type { TwoFactorMethod } from '../../types'

interface Props {
  availableMethods: TwoFactorMethod[]
  onSuccess: () => void
}

export function TwoFactorVerify({ availableMethods, onSuccess }: Props) {
  const [selectedMethod, setSelectedMethod] = useState(availableMethods[0])
  const [code, setCode] = useState('')
  const [trustDevice, setTrustDevice] = useState(false)
  
  const verify = useTwoFactorVerify()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await verify.mutateAsync({
      method: selectedMethod,
      code,
      trustDevice,
    })
    onSuccess()
  }
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Verification UI */}
    </form>
  )
}
```

**Hook:**
```typescript
// features/twofa/hooks/useTwoFactorVerify.ts
import { useMutation } from '@tanstack/react-query'
import { twofaClient } from '../api/twofaClient'
import type { TwoFactorVerifyRequest } from '../types'

export function useTwoFactorVerify() {
  return useMutation({
    mutationFn: (data: TwoFactorVerifyRequest) => twofaClient.verify(data),
  })
}
```

**Definition of Done:**
- [ ] Verification component created
- [ ] Hook created
- [ ] All methods can be verified
- [ ] Error states handled
- [ ] Trust device working
- [ ] Recovery code option available

---

### Story 3.5: Migrate 2FA Settings Components

**As a** frontend developer  
**I want** 2FA management components in the feature  
**So that** users can manage their 2FA settings

**Acceptance Criteria:**
1. Settings page components migrated
2. Status display working
3. Disable 2FA working
4. Recovery codes management working
5. Trusted devices management working

**Components to Migrate:**
- `TwoFactorSettings.tsx` - Main settings page
- `TwoFactorStatusHeader.tsx` - Shows enabled status
- `TwoFactorEnabledSettings.tsx` - Settings when enabled
- `DisableTwoFactorSection.tsx` - Disable functionality
- `RecoveryCodesSection.tsx` - Recovery codes management
- `RecoveryCodeList.tsx` - Display recovery codes
- `TrustedDevicesSection.tsx` - Trusted devices list

**Hooks:**
```typescript
// features/twofa/hooks/useTwoFactorStatus.ts
import { useQuery } from '@tanstack/react-query'
import { twofaClient } from '../api/twofaClient'

export function useTwoFactorStatus() {
  return useQuery({
    queryKey: ['twofa', 'status'],
    queryFn: () => twofaClient.getStatus(),
  })
}
```

```typescript
// features/twofa/hooks/useRecoveryCodes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { twofaClient } from '../api/twofaClient'

export function useRecoveryCodes() {
  const queryClient = useQueryClient()
  
  const codes = useQuery({
    queryKey: ['twofa', 'recoveryCodes'],
    queryFn: () => twofaClient.getRecoveryCodes(),
  })
  
  const regenerate = useMutation({
    mutationFn: () => twofaClient.regenerateRecoveryCodes(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['twofa', 'recoveryCodes'] })
    },
  })
  
  return { codes, regenerate }
}
```

**Definition of Done:**
- [ ] All settings components migrated
- [ ] Hooks created
- [ ] Status display working
- [ ] Disable functionality working
- [ ] Recovery codes can be viewed
- [ ] Recovery codes can be regenerated
- [ ] Trusted devices listed
- [ ] Devices can be removed

---

### Story 3.6: Update Routes and Imports

**As a** frontend developer  
**I want** all 2FA route files updated  
**So that** they use the new feature structure

**Acceptance Criteria:**
1. All route files updated
2. All imports pointing to features
3. No references to old modules
4. TypeScript compilation succeeds
5. All 2FA routes working

**Routes to Update:**
- `routes/2fa/settings.tsx`
- `routes/2fa/setup/index.tsx`
- `routes/2fa/setup/email.tsx`
- `routes/2fa/setup/sms.tsx`
- `routes/2fa/setup/totp.tsx`
- `routes/2fa/verify.tsx`
- `routes/2fa/trusted-devices.tsx`

**Example Update:**
```typescript
// routes/2fa/settings.tsx (BEFORE)
import { TwoFactorSettings } from '@/modules/twofa/components/TwoFactorSettings'

// routes/2fa/settings.tsx (AFTER)
import { createFileRoute } from '@tanstack/react-router'
import { TwoFactorSettings } from '@/features/twofa'
import { ProtectedRoute } from '@/components'

export const Route = createFileRoute('/2fa/settings')({
  component: TwoFactorSettingsPage,
})

function TwoFactorSettingsPage() {
  return (
    <ProtectedRoute>
      <div className="container-page py-8">
        <TwoFactorSettings />
      </div>
    </ProtectedRoute>
  )
}
```

**Import Migration:**
```bash
#!/bin/bash
# Update all 2FA imports

find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i \
  's|from "@/modules/twofa|from "@/features/twofa|g' {} +

echo "✅ 2FA imports updated"
```

**Definition of Done:**
- [ ] All route files updated
- [ ] All imports updated
- [ ] TypeScript compiles
- [ ] All routes accessible
- [ ] All 2FA flows working

---

### Story 3.7: Clean Up and Final Testing

**As a** frontend developer  
**I want** old 2FA module removed and everything tested  
**So that** the migration is complete and verified

**Acceptance Criteria:**
1. Old `modules/twofa/` directory removed
2. No references to old paths
3. All 2FA flows tested end-to-end
4. Documentation updated
5. Feature exports validated

**Testing Checklist:**
- [ ] Setup TOTP - complete wizard
- [ ] Setup Email - complete wizard
- [ ] Setup SMS - complete wizard
- [ ] Verify with TOTP during login
- [ ] Verify with Email during login
- [ ] Verify with SMS during login
- [ ] Use recovery code
- [ ] View 2FA status
- [ ] Regenerate recovery codes
- [ ] View trusted devices
- [ ] Remove trusted device
- [ ] Disable 2FA

**Export Validation:**
```typescript
// features/twofa/index.ts
// Verify these exports are clean and complete

// Setup components
export { TwoFactorSetup } from './components/setup/TwoFactorSetup'

// Verification components
export { TwoFactorVerify } from './components/verify/TwoFactorVerify'

// Settings components
export { TwoFactorSettings } from './components/settings/TwoFactorSettings'

// Hooks
export { useTwoFactorSetup } from './hooks/useTwoFactorSetup'
export { useTwoFactorVerify } from './hooks/useTwoFactorVerify'
export { useTwoFactorStatus } from './hooks/useTwoFactorStatus'
export { useRecoveryCodes } from './hooks/useRecoveryCodes'
export { useTrustedDevices } from './hooks/useTrustedDevices'

// Types (public only)
export type {
  TwoFactorMethod,
  TwoFactorStatus,
  TrustedDevice,
} from './types/twofa.types'
```

**Definition of Done:**
- [ ] Old directory removed
- [ ] No old path references
- [ ] All tests passing
- [ ] All flows tested manually
- [ ] Exports validated
- [ ] Documentation updated

---

## Testing Strategy

### Component Testing
- [ ] Test each setup step component
- [ ] Test verification components
- [ ] Test settings components
- [ ] Test state management in wizards

### Integration Testing
- [ ] Complete TOTP setup flow
- [ ] Complete Email setup flow
- [ ] Complete SMS setup flow
- [ ] Verification during login
- [ ] Recovery code usage
- [ ] Trusted device management

### User Flow Testing
- [ ] New user sets up 2FA
- [ ] Existing user enables additional method
- [ ] User verifies during login
- [ ] User regenerates recovery codes
- [ ] User disables 2FA

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Complex component nesting breaks | High | Medium | Careful migration, preserve structure exactly |
| Setup wizard state lost | High | Low | Test state management thoroughly |
| Recovery codes not working | Critical | Low | Comprehensive testing of recovery flows |
| Trusted devices broken | Medium | Low | Test device management extensively |

---

## Dependencies

**Requires**: FE-ARCH-002 (Auth Migration)

**Blocks**: FE-ARCH-004 (Tooling & Docs)

---

## Definition of Done

- [ ] All 7 stories completed
- [ ] All 2FA code in `features/twofa/`
- [ ] No code in `modules/twofa/`
- [ ] All routes updated
- [ ] All flows tested
- [ ] Documentation updated

---

**Last Updated**: 2025-01-15  
**Epic Owner**: Frontend Team
