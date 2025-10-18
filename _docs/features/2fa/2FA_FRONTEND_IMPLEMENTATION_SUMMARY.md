# 2FA Frontend Implementation Summary

## Overview

This document provides a quick reference for implementing Two-Factor Authentication (2FA) in the Tinybeans React Vite frontend application.

## Documentation

- **[ADR-003: 2FA Backend Architecture](./ADR-003-TWO-FACTOR-AUTHENTICATION.md)** - Complete backend implementation
- **[ADR-004: 2FA Frontend Implementation](./ADR-004-2FA-FRONTEND-IMPLEMENTATION.md)** - This frontend implementation guide
- **[2FA Implementation Status](./2FA_IMPLEMENTATION_STATUS.md)** - Current implementation status

## Quick Start

### Key Technologies

- **React 19** + **TypeScript**
- **TanStack Router** - Routing
- **TanStack Query** - Server state management
- **TanStack Form** - Form handling
- **TanStack Store** - Client state
- **Radix UI** - Accessible components
- **Tailwind CSS** - Styling

### Module Structure

```
web/src/features/twofa/
├── client.ts                    # API functions
├── hooks.ts                     # React Query hooks
├── store.ts                     # State management
├── types.ts                     # TypeScript definitions
├── routes.2fa-setup.tsx         # Setup page
├── routes.2fa-verify.tsx        # Verification page
├── routes.2fa-settings.tsx      # Settings page
├── routes.recovery-codes.tsx    # Recovery codes
├── routes.trusted-devices.tsx   # Trusted devices
└── components/
    ├── TotpSetup.tsx            # TOTP setup wizard
    ├── EmailSetup.tsx           # Email setup
    ├── SmsSetup.tsx             # SMS setup
    ├── VerificationInput.tsx    # 6-digit code input
    ├── RecoveryCodeList.tsx     # Display codes
    ├── TrustedDeviceList.tsx    # Device list
    ├── QRCodeDisplay.tsx        # QR code display
    └── RememberDeviceCheckbox.tsx
```

## Key Features

### 1. Three 2FA Methods

- **TOTP (Authenticator App)** - Primary method, works offline
- **Email OTP** - Fallback method
- **SMS OTP** - Alternative method

### 2. Recovery Codes

- 10 single-use codes generated at setup
- Downloadable as TXT or PDF
- Regenerate option available

### 3. Trusted Devices

- "Remember this device for 30 days"
- Manage devices in settings
- Remove devices remotely

### 4. Complete User Flows

- ✅ Setup 2FA (all methods)
- ✅ Login with 2FA
- ✅ Use recovery codes
- ✅ Manage settings
- ✅ Manage trusted devices

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Create `twofa` module directory
- [ ] Implement API client (`client.ts`)
- [ ] Define TypeScript types (`types.ts`)
- [ ] Create TanStack Store (`store.ts`)
- [ ] Create React Query hooks (`hooks.ts`)

### Phase 2: Components
- [ ] `VerificationInput` - 6-digit code input
- [ ] `QRCodeDisplay` - Display QR code
- [ ] `RecoveryCodeList` - Display recovery codes
- [ ] `TotpSetup` - TOTP setup wizard
- [ ] `EmailSetup` - Email setup
- [ ] `SmsSetup` - SMS setup
- [ ] `TrustedDeviceList` - Device management

### Phase 3: Pages/Routes
- [ ] Setup page (`routes.2fa-setup.tsx`)
- [ ] Verification page (`routes.2fa-verify.tsx`)
- [ ] Settings page (`routes.2fa-settings.tsx`)
- [ ] Recovery codes page (`routes.recovery-codes.tsx`)
- [ ] Trusted devices page (`routes.trusted-devices.tsx`)

### Phase 4: Login Integration
- [ ] Modify `useLogin` hook for 2FA flow
- [ ] Handle `requires_2fa` response
- [ ] Store partial token
- [ ] Navigate to verification
- [ ] Handle device_id

### Phase 5: Polish
- [ ] Error handling
- [ ] Loading states
- [ ] Responsive design
- [ ] Accessibility
- [ ] Testing

## Key Code Examples

### API Client Setup

```typescript
// twofa/client.ts
import { api } from '../login/client'

export const twoFactorApi = {
  initializeSetup: (method: 'totp' | 'email' | 'sms') =>
    api.post('/auth/2fa/setup/', { method }),
  
  verify: (code: string, remember_me: boolean) =>
    api.post('/auth/2fa/verify/', { code, remember_me }),
  
  getStatus: () =>
    api.get('/auth/2fa/status/'),
}
```

### React Query Hook

```typescript
// twofa/hooks.ts
export function useVerify2FA() {
  return useMutation({
    mutationFn: ({ code, remember_me }) =>
      twoFactorApi.verify(code, remember_me),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access)
      if (data.device_id) {
        localStorage.setItem('device_id', data.device_id)
      }
    },
  })
}
```

### Verification Component

```tsx
// components/VerificationInput.tsx
export function VerificationInput({ 
  value, 
  onChange, 
  onComplete 
}) {
  // 6 separate input fields
  // Auto-focus next on input
  // Handle paste
  // Call onComplete when all filled
}
```

### Enhanced Login Flow

```typescript
// Modify login/hooks.ts
export function useLogin() {
  return useMutation({
    mutationFn: (credentials) => api.post('/auth/login/', credentials),
    onSuccess: (data) => {
      if (data.requires_2fa) {
        // Store partial token
        setPartialToken(data.partial_token)
        setTwoFactorMethod(data.method)
        // Navigate to /2fa/verify
        navigate({ to: '/2fa/verify' })
      } else {
        // Normal login
        setAccessToken(data.tokens.access)
      }
    },
  })
}
```

## User Flows

### Enable TOTP (Authenticator App)

1. Navigate to `/2fa/setup`
2. Select "Authenticator App"
3. Backend generates TOTP secret
4. Display QR code
5. User scans with authenticator app
6. User enters 6-digit code
7. Backend validates code
8. Display 10 recovery codes
9. User downloads/saves codes
10. 2FA enabled

### Login with 2FA

1. User enters username/password
2. Check for trusted device
3. If not trusted:
   - Backend sends OTP (email/SMS) or expects TOTP
   - Return `requires_2fa: true` + `partial_token`
4. Navigate to `/2fa/verify`
5. User enters 6-digit code
6. Optional: Check "Remember device"
7. Backend validates code
8. Return full tokens + device_id (if remember)
9. Store tokens and device_id
10. Redirect to homepage

### Use Recovery Code

1. On verification page
2. Click "Use recovery code"
3. Enter recovery code (XXXX-XXXX-XXXX)
4. Backend validates and marks as used
5. Login successful
6. Alert email sent

## API Endpoints

```
POST   /auth/2fa/setup/                  - Initialize setup
POST   /auth/2fa/verify-setup/           - Verify and enable
GET    /auth/2fa/status/                 - Get settings
POST   /auth/2fa/verify/                 - Verify login
POST   /auth/2fa/disable/                - Disable 2FA
POST   /auth/2fa/send-code/              - Resend OTP
POST   /auth/2fa/recovery-codes/generate/     - Generate new codes
GET    /auth/2fa/recovery-codes/download/     - Download codes
POST   /auth/2fa/recovery-codes/verify/       - Use recovery code
GET    /auth/2fa/trusted-devices/             - List devices
POST   /auth/2fa/trusted-devices/remove/      - Remove device
```

## Testing Strategy

### Unit Tests
- API client functions
- React Query hooks
- Components in isolation
- State management

### Integration Tests
- Complete setup flows
- Login with 2FA
- Recovery code usage
- Device management

### E2E Tests
- Full user journey
- Error scenarios
- Multi-device scenarios
- Accessibility

## Styling Guidelines

- Use Tailwind CSS utility classes
- Follow existing design system
- Mobile-first responsive design
- Accessible color contrasts
- Clear focus indicators
- Loading and error states

## Accessibility

- ✅ Keyboard navigation
- ✅ Screen reader support
- ✅ ARIA labels and live regions
- ✅ Focus management
- ✅ Error announcements
- ✅ Semantic HTML
- ✅ High contrast support

## Performance

- Code splitting for 2FA module
- Lazy loading components
- Optimized QR code size
- React Query caching
- Memoization where needed
- Prefetch on login page

## Security

- Partial tokens with limited scope
- HTTPS only
- No code logging
- Clear sensitive data on logout
- Secure device_id storage
- Rate limiting feedback
- Clear security warnings

## Timeline

**Total Estimated: 28-39 hours**

- Phase 1: Core (4-6h)
- Phase 2: Components (6-8h)
- Phase 3: Routes (8-10h)
- Phase 4: Integration (4-6h)
- Phase 5: Polish (4-6h)
- Phase 6: Documentation (2-3h)

## Next Steps

1. ✅ Review and approve ADR-004
2. Create GitHub issue/project
3. Set up module structure
4. Begin Phase 1 implementation
5. Iterative development and testing
6. User acceptance testing
7. Deploy and monitor

## Resources

- [ADR-004 Full Document](./ADR-004-2FA-FRONTEND-IMPLEMENTATION.md)
- [Backend ADR-003](./ADR-003-TWO-FACTOR-AUTHENTICATION.md)
- [TanStack Documentation](https://tanstack.com/)
- [Radix UI Components](https://www.radix-ui.com/)
- [OWASP 2FA Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)

## Questions?

For questions or clarifications:
1. Review the full ADR-004 document
2. Check existing auth implementation in `web/src/features/auth/`
3. Refer to backend implementation docs
4. Test with backend API endpoints

---

**Last Updated:** 2025-01-08
**Status:** Ready for Implementation
