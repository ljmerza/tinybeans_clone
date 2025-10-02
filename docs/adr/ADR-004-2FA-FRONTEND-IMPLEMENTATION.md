# ADR-004: Two-Factor Authentication (2FA) Frontend Implementation

## Status
**Proposed** - *Date: 2025-01-08*

## Context

The backend implementation of Two-Factor Authentication (2FA) has been completed in Phase 1 (see [ADR-003](./ADR-003-TWO-FACTOR-AUTHENTICATION.md) and [2FA_IMPLEMENTATION_STATUS.md](./2FA_IMPLEMENTATION_STATUS.md)). We now need to implement the frontend user interface and flows for the 2FA feature in the React Vite web application using TanStack libraries.

### Current Frontend Architecture

**Tech Stack:**
- **React 19.0.0** - UI library
- **Vite 7.1.7** - Build tool and dev server
- **TypeScript 5.7.2** - Type safety
- **TanStack Router 1.132.0** - Routing
- **TanStack Query 5.66.5** - Server state management
- **TanStack Form 1.0.0** - Form handling
- **TanStack Store 0.7.0** - Client state management
- **Zod 3.24.2** - Schema validation
- **Tailwind CSS 4.0.6** - Styling
- **Radix UI** - Accessible component primitives
- **Lucide React** - Icon library

**Existing Auth Module Structure:**
```
web/src/modules/login/
├── client.ts              # API client with auth interceptor
├── hooks.ts               # useLogin, useSignup, useLogout hooks
├── routes.login.tsx       # Login page component
├── routes.logout.tsx      # Logout component
├── routes.signup.tsx      # Signup page component
├── store.ts               # Auth store (accessToken, user)
└── devtools.tsx           # Development tools
```

**Current Authentication Flow:**
1. User submits credentials via `useLogin` hook
2. API client sends POST to `/auth/login/`
3. Receives `{access, refresh}` tokens
4. Stores access token in TanStack Store
5. Refresh token stored in HTTP-only cookie
6. Auto-refresh on 401 responses

### Requirements

The frontend must support:

1. **Setup Flows** - Enable 2FA with TOTP, Email, or SMS
2. **Login Flow** - Handle 2FA verification during login
3. **Recovery Flow** - Use recovery codes when 2FA unavailable
4. **Management UI** - Enable/disable 2FA, manage trusted devices
5. **Recovery Code Management** - Display, download (TXT/PDF), regenerate codes
6. **Trusted Devices** - "Remember this device" functionality
7. **Responsive Design** - Mobile-first approach
8. **Accessibility** - WCAG 2.1 AA compliance
9. **Error Handling** - Clear feedback and recovery paths
10. **Loading States** - Proper UX during async operations

## Decision

We will implement a comprehensive 2FA frontend module following the existing architecture patterns and leveraging TanStack libraries for state management, routing, and forms.

### Architecture Overview

```
web/src/modules/twofa/
├── client.ts                    # 2FA API client functions
├── hooks.ts                     # React Query hooks for 2FA operations
├── store.ts                     # 2FA state (partialToken, method, etc.)
├── types.ts                     # TypeScript types/interfaces
├── routes.2fa-setup.tsx         # 2FA setup page (choose method)
├── routes.2fa-verify.tsx        # 2FA verification during login
├── routes.2fa-settings.tsx      # Manage 2FA settings
├── routes.recovery-codes.tsx    # View/download recovery codes
├── routes.trusted-devices.tsx   # Manage trusted devices
└── components/
    ├── TotpSetup.tsx            # TOTP/Authenticator app setup
    ├── EmailSetup.tsx           # Email 2FA setup
    ├── SmsSetup.tsx             # SMS 2FA setup
    ├── VerificationInput.tsx    # 6-digit code input component
    ├── RecoveryCodeList.tsx     # Display recovery codes
    ├── TrustedDeviceList.tsx    # List of trusted devices
    ├── QRCodeDisplay.tsx        # Display QR code for TOTP
    └── RememberDeviceCheckbox.tsx # Remember device checkbox
```

### Component Breakdown

#### 1. API Client (`twofa/client.ts`)

```typescript
import { api } from '../login/client'

export interface TwoFactorSetupResponse {
  method: 'totp' | 'email' | 'sms'
  secret?: string
  qr_code?: string
  qr_code_image?: string
  message?: string
  expires_in?: number
}

export interface TwoFactorStatusResponse {
  is_enabled: boolean
  preferred_method: 'totp' | 'email' | 'sms'
  phone_number?: string
  backup_email?: string
  created_at: string
  updated_at: string
}

export interface TwoFactorVerifyResponse {
  tokens: {
    access: string
    refresh: string
  }
  user: {
    id: number
    username: string
    email: string
  }
  device_id?: string
  device_trust_expires?: string
}

export interface RecoveryCodesResponse {
  recovery_codes: string[]
}

export interface TrustedDevice {
  device_id: string
  device_name: string
  ip_address: string
  last_used_at: string
  expires_at: string
  created_at: string
}

export const twoFactorApi = {
  // Setup
  initializeSetup: (method: 'totp' | 'email' | 'sms', phone_number?: string) =>
    api.post<TwoFactorSetupResponse>('/auth/2fa/setup/', { method, phone_number }),

  verifySetup: (code: string) =>
    api.post<RecoveryCodesResponse>('/auth/2fa/verify-setup/', { code }),

  // Status
  getStatus: () =>
    api.get<TwoFactorStatusResponse>('/auth/2fa/status/'),

  // Verification
  verify: (code: string, remember_me: boolean = false) =>
    api.post<TwoFactorVerifyResponse>('/auth/2fa/verify/', { code, remember_me }),

  // Disable
  disable: (code: string) =>
    api.post<{ message: string }>('/auth/2fa/disable/', { code }),

  // Recovery Codes
  generateRecoveryCodes: () =>
    api.post<RecoveryCodesResponse>('/auth/2fa/recovery-codes/generate/', {}),

  downloadRecoveryCodes: (format: 'txt' | 'pdf') => {
    const url = `${import.meta.env.VITE_API_BASE}/auth/2fa/recovery-codes/download/?format=${format}`
    window.open(url, '_blank')
  },

  verifyRecoveryCode: (code: string, remember_me: boolean = false) =>
    api.post<TwoFactorVerifyResponse>('/auth/2fa/recovery-codes/verify/', { code, remember_me }),

  // Trusted Devices
  getTrustedDevices: () =>
    api.get<{ devices: TrustedDevice[] }>('/auth/2fa/trusted-devices/'),

  removeTrustedDevice: (device_id: string) =>
    api.post<{ message: string }>('/auth/2fa/trusted-devices/remove/', { device_id }),

  // Resend code (for email/SMS)
  resendCode: () =>
    api.post<{ message: string; expires_in: number }>('/auth/2fa/send-code/', {}),
}
```

#### 2. React Query Hooks (`twofa/hooks.ts`)

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { twoFactorApi } from './client'
import { twoFactorStore, setPartialToken, setTwoFactorMethod, clearTwoFactorState } from './store'

// Setup hooks
export function useInitialize2FASetup() {
  return useMutation({
    mutationFn: ({ method, phone_number }: { method: 'totp' | 'email' | 'sms'; phone_number?: string }) =>
      twoFactorApi.initializeSetup(method, phone_number),
    onSuccess: (data) => {
      setTwoFactorMethod(data.method)
    },
  })
}

export function useVerify2FASetup() {
  return useMutation({
    mutationFn: (code: string) => twoFactorApi.verifySetup(code),
  })
}

// Status hooks
export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa', 'status'],
    queryFn: () => twoFactorApi.getStatus(),
  })
}

// Verification hook
export function useVerify2FA() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ code, remember_me }: { code: string; remember_me?: boolean }) =>
      twoFactorApi.verify(code, remember_me),
    onSuccess: (data) => {
      // Store access token
      const { setAccessToken } = await import('../login/store')
      setAccessToken(data.tokens.access)
      
      // Store device_id if provided
      if (data.device_id) {
        localStorage.setItem('device_id', data.device_id)
      }
      
      // Clear 2FA state
      clearTwoFactorState()
      
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })
}

// Disable hook
export function useDisable2FA() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (code: string) => twoFactorApi.disable(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa', 'status'] })
    },
  })
}

// Recovery codes hooks
export function useGenerateRecoveryCodes() {
  return useMutation({
    mutationFn: () => twoFactorApi.generateRecoveryCodes(),
  })
}

export function useVerifyRecoveryCode() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ code, remember_me }: { code: string; remember_me?: boolean }) =>
      twoFactorApi.verifyRecoveryCode(code, remember_me),
    onSuccess: (data) => {
      const { setAccessToken } = await import('../login/store')
      setAccessToken(data.tokens.access)
      
      if (data.device_id) {
        localStorage.setItem('device_id', data.device_id)
      }
      
      clearTwoFactorState()
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })
}

// Trusted devices hooks
export function useTrustedDevices() {
  return useQuery({
    queryKey: ['2fa', 'trusted-devices'],
    queryFn: () => twoFactorApi.getTrustedDevices(),
  })
}

export function useRemoveTrustedDevice() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (device_id: string) => twoFactorApi.removeTrustedDevice(device_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa', 'trusted-devices'] })
    },
  })
}

// Resend code hook
export function useResendCode() {
  return useMutation({
    mutationFn: () => twoFactorApi.resendCode(),
  })
}
```

#### 3. State Management (`twofa/store.ts`)

```typescript
import { Store } from '@tanstack/store'

interface TwoFactorState {
  partialToken: string | null
  method: 'totp' | 'email' | 'sms' | null
  requiresVerification: boolean
  setupInProgress: boolean
}

export const twoFactorStore = new Store<TwoFactorState>({
  partialToken: null,
  method: null,
  requiresVerification: false,
  setupInProgress: false,
})

export function setPartialToken(token: string | null) {
  twoFactorStore.setState((state) => ({ ...state, partialToken: token }))
}

export function setTwoFactorMethod(method: 'totp' | 'email' | 'sms' | null) {
  twoFactorStore.setState((state) => ({ ...state, method }))
}

export function setRequiresVerification(requires: boolean) {
  twoFactorStore.setState((state) => ({ ...state, requiresVerification: requires }))
}

export function setSetupInProgress(inProgress: boolean) {
  twoFactorStore.setState((state) => ({ ...state, setupInProgress: inProgress }))
}

export function clearTwoFactorState() {
  twoFactorStore.setState({
    partialToken: null,
    method: null,
    requiresVerification: false,
    setupInProgress: false,
  })
}
```

#### 4. Enhanced Login Flow (`login/hooks.ts` modification)

```typescript
// Modify useLogin hook to handle 2FA
export function useLogin() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const response = await api.post('/auth/login/', credentials)
      return response
    },
    onSuccess: (data: any) => {
      // Check if 2FA is required
      if (data.requires_2fa) {
        // Store partial token and method
        const { setPartialToken, setTwoFactorMethod, setRequiresVerification } = 
          await import('../twofa/store')
        
        setPartialToken(data.partial_token)
        setTwoFactorMethod(data.method)
        setRequiresVerification(true)
        
        // Navigate to 2FA verification
        navigate({ to: '/2fa/verify' })
      } else {
        // Normal login without 2FA
        setAccessToken(data.tokens.access)
        // Continue as usual
      }
    },
  })
}
```

#### 5. Key Components

##### VerificationInput Component

```tsx
// components/VerificationInput.tsx
import { useState, useRef, useEffect } from 'react'
import { Input } from '@/components/ui/input'

interface VerificationInputProps {
  length?: number
  value: string
  onChange: (value: string) => void
  onComplete?: (value: string) => void
  autoFocus?: boolean
}

export function VerificationInput({
  length = 6,
  value,
  onChange,
  onComplete,
  autoFocus = true,
}: VerificationInputProps) {
  const [digits, setDigits] = useState<string[]>(Array(length).fill(''))
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus()
    }
  }, [autoFocus])

  const handleChange = (index: number, digit: string) => {
    // Only allow digits
    if (digit && !/^\d$/.test(digit)) return

    const newDigits = [...digits]
    newDigits[index] = digit

    setDigits(newDigits)
    const newValue = newDigits.join('')
    onChange(newValue)

    // Auto-focus next input
    if (digit && index < length - 1) {
      inputRefs.current[index + 1]?.focus()
    }

    // Call onComplete when all digits entered
    if (newValue.length === length && onComplete) {
      onComplete(newValue)
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
    const newDigits = pastedData.split('').concat(Array(length).fill('')).slice(0, length)
    setDigits(newDigits)
    onChange(newDigits.join(''))

    if (pastedData.length === length && onComplete) {
      onComplete(pastedData)
    }
  }

  return (
    <div className="flex gap-2 justify-center" onPaste={handlePaste}>
      {Array.from({ length }).map((_, index) => (
        <Input
          key={index}
          ref={(el) => (inputRefs.current[index] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digits[index]}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          className="w-12 h-12 text-center text-2xl"
          aria-label={`Digit ${index + 1}`}
        />
      ))}
    </div>
  )
}
```

##### TOTP Setup Component

```tsx
// components/TotpSetup.tsx
import { useState } from 'react'
import { useInitialize2FASetup, useVerify2FASetup } from '../hooks'
import { Button } from '@/components/ui/button'
import { QRCodeDisplay } from './QRCodeDisplay'
import { VerificationInput } from './VerificationInput'
import { RecoveryCodeList } from './RecoveryCodeList'

interface TotpSetupProps {
  onComplete?: () => void
}

export function TotpSetup({ onComplete }: TotpSetupProps) {
  const [step, setStep] = useState<'initial' | 'scan' | 'verify' | 'recovery'>('initial')
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [secret, setSecret] = useState<string>('')
  const [verificationCode, setVerificationCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])

  const initSetup = useInitialize2FASetup()
  const verifySetup = useVerify2FASetup()

  const handleInitialize = async () => {
    try {
      const response = await initSetup.mutateAsync({ method: 'totp' })
      setQrCode(response.qr_code_image || null)
      setSecret(response.secret || '')
      setStep('scan')
    } catch (error) {
      // Handle error
    }
  }

  const handleVerify = async () => {
    try {
      const response = await verifySetup.mutateAsync(verificationCode)
      setRecoveryCodes(response.recovery_codes)
      setStep('recovery')
    } catch (error) {
      // Handle error
    }
  }

  const handleComplete = () => {
    onComplete?.()
  }

  return (
    <div className="space-y-6">
      {step === 'initial' && (
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-4">Set up Authenticator App</h2>
          <p className="text-gray-600 mb-6">
            Use an authenticator app like Google Authenticator, Authy, or 1Password
            to generate verification codes.
          </p>
          <Button onClick={handleInitialize} disabled={initSetup.isPending}>
            {initSetup.isPending ? 'Setting up...' : 'Start Setup'}
          </Button>
        </div>
      )}

      {step === 'scan' && qrCode && (
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-4">Scan QR Code</h2>
          <QRCodeDisplay qrCode={qrCode} secret={secret} />
          <Button onClick={() => setStep('verify')} className="mt-6">
            I've scanned the code
          </Button>
        </div>
      )}

      {step === 'verify' && (
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-4">Verify Setup</h2>
          <p className="text-gray-600 mb-6">
            Enter the 6-digit code from your authenticator app
          </p>
          <VerificationInput
            value={verificationCode}
            onChange={setVerificationCode}
            onComplete={handleVerify}
          />
          <Button
            onClick={handleVerify}
            disabled={verificationCode.length !== 6 || verifySetup.isPending}
            className="mt-6"
          >
            {verifySetup.isPending ? 'Verifying...' : 'Verify & Enable'}
          </Button>
        </div>
      )}

      {step === 'recovery' && recoveryCodes.length > 0 && (
        <div>
          <h2 className="text-2xl font-semibold mb-4">Save Recovery Codes</h2>
          <RecoveryCodeList codes={recoveryCodes} />
          <Button onClick={handleComplete} className="w-full mt-6">
            I've saved my codes
          </Button>
        </div>
      )}
    </div>
  )
}
```

##### 2FA Verification Page

```tsx
// routes.2fa-verify.tsx
import { createRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useStore } from '@tanstack/react-store'
import { twoFactorStore } from './store'
import { useVerify2FA, useResendCode, useVerifyRecoveryCode } from './hooks'
import { VerificationInput } from './components/VerificationInput'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

function TwoFactorVerifyPage() {
  const navigate = useNavigate()
  const { method, partialToken } = useStore(twoFactorStore)
  const [code, setCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [useRecoveryCode, setUseRecoveryCode] = useState(false)

  const verify = useVerify2FA()
  const verifyRecovery = useVerifyRecoveryCode()
  const resend = useResendCode()

  if (!method || !partialToken) {
    navigate({ to: '/login' })
    return null
  }

  const handleVerify = async () => {
    try {
      if (useRecoveryCode) {
        await verifyRecovery.mutateAsync({ code, remember_me: rememberMe })
      } else {
        await verify.mutateAsync({ code, remember_me: rememberMe })
      }
      navigate({ to: '/' })
    } catch (error) {
      // Error handled by mutation
    }
  }

  const handleResend = async () => {
    if (method === 'totp') return // Cannot resend TOTP
    try {
      await resend.mutateAsync()
    } catch (error) {
      // Error handled
    }
  }

  const getMethodDisplay = () => {
    if (useRecoveryCode) return 'recovery code'
    switch (method) {
      case 'totp': return 'authenticator app'
      case 'email': return 'email'
      case 'sms': return 'phone'
      default: return method
    }
  }

  return (
    <div className="max-w-md mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Two-Factor Authentication</h1>
      
      {!useRecoveryCode && (
        <p className="text-gray-600 mb-6">
          Enter the 6-digit code from your {getMethodDisplay()}
        </p>
      )}

      {useRecoveryCode && (
        <p className="text-gray-600 mb-6">
          Enter one of your recovery codes
        </p>
      )}

      <div className="space-y-6">
        <VerificationInput
          value={code}
          onChange={setCode}
          onComplete={handleVerify}
        />

        <div className="flex items-center space-x-2">
          <Checkbox
            id="remember-me"
            checked={rememberMe}
            onCheckedChange={(checked) => setRememberMe(checked === true)}
          />
          <Label htmlFor="remember-me" className="text-sm">
            Remember this device for 30 days
          </Label>
        </div>

        <Button
          onClick={handleVerify}
          disabled={code.length !== 6 || verify.isPending || verifyRecovery.isPending}
          className="w-full"
        >
          {verify.isPending || verifyRecovery.isPending ? 'Verifying...' : 'Verify'}
        </Button>

        {verify.error && (
          <p className="text-sm text-red-600 text-center">
            {(verify.error as any)?.message || 'Invalid code'}
          </p>
        )}

        {method !== 'totp' && !useRecoveryCode && (
          <Button
            variant="ghost"
            onClick={handleResend}
            disabled={resend.isPending}
            className="w-full"
          >
            {resend.isPending ? 'Sending...' : 'Resend Code'}
          </Button>
        )}

        <div className="text-center">
          <button
            type="button"
            onClick={() => setUseRecoveryCode(!useRecoveryCode)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {useRecoveryCode ? 'Use verification code' : 'Use recovery code'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default (parentRoute: any) =>
  createRoute({
    path: '/2fa/verify',
    component: TwoFactorVerifyPage,
    getParentRoute: () => parentRoute,
  })
```

### User Flows

#### 1. Enable 2FA (TOTP)
```
1. User navigates to /2fa/setup
2. User selects "Authenticator App"
3. System calls POST /auth/2fa/setup/ {method: 'totp'}
4. System displays QR code + manual secret
5. User scans QR with authenticator app
6. User enters 6-digit code from app
7. System calls POST /auth/2fa/verify-setup/ {code}
8. System displays recovery codes
9. User downloads/saves codes
10. User clicks "Done"
11. 2FA enabled, redirect to settings
```

#### 2. Login with 2FA
```
1. User enters username/password
2. System checks for device_id in localStorage
3a. If trusted device: Skip to step 8
3b. If not trusted: Continue to step 4
4. System calls POST /auth/login/ (receives requires_2fa: true)
5. Store partial token, method in TanStack Store
6. Navigate to /2fa/verify
7. User enters code + optionally checks "Remember device"
8. System calls POST /auth/2fa/verify/ {code, remember_me}
9. System stores access token + device_id
10. Navigate to homepage
```

#### 3. Use Recovery Code
```
1. During login 2FA verification
2. User clicks "Use recovery code"
3. UI switches to recovery code input
4. User enters recovery code (format: XXXX-XXXX-XXXX)
5. System calls POST /auth/2fa/recovery-codes/verify/ {code}
6. System validates and marks code as used
7. Login successful
8. Alert email sent to user
```

#### 4. Manage Trusted Devices
```
1. User navigates to /2fa/trusted-devices
2. System calls GET /auth/2fa/trusted-devices/
3. Display list with device name, last used, expires
4. User clicks "Remove" on a device
5. System calls POST /auth/2fa/trusted-devices/remove/ {device_id}
6. Device removed from list
7. Next login from that device requires 2FA
```

### Routing Configuration

```typescript
// Add to routeTree or routes configuration
const twoFaRoutes = [
  { path: '/2fa/setup', component: TwoFactorSetupPage },
  { path: '/2fa/verify', component: TwoFactorVerifyPage },
  { path: '/2fa/settings', component: TwoFactorSettingsPage },
  { path: '/2fa/recovery-codes', component: RecoveryCodesPage },
  { path: '/2fa/trusted-devices', component: TrustedDevicesPage },
]
```

### Error Handling Strategy

1. **Network Errors**: Toast notification + retry button
2. **Invalid Code**: Inline error message + clear input
3. **Expired Code**: Prompt to resend (email/SMS only)
4. **Rate Limiting**: Display cooldown timer
5. **Account Locked**: Redirect to support page
6. **Missing Partial Token**: Redirect to login
7. **API Errors**: Graceful degradation + error boundary

### Accessibility Features

1. **Keyboard Navigation**: Full support with focus management
2. **Screen Reader**: ARIA labels and live regions
3. **High Contrast**: Compatible color schemes
4. **Focus Indicators**: Clear visual focus states
5. **Error Announcements**: Screen reader announces errors
6. **Skip Links**: Skip to main content
7. **Semantic HTML**: Proper heading hierarchy

### Mobile Considerations

1. **Responsive Design**: Mobile-first approach
2. **Touch Targets**: Minimum 44x44px
3. **Input Types**: `inputMode="numeric"` for code inputs
4. **Auto-focus**: Focus first input on mobile
5. **SMS Auto-fill**: Support OTP autocomplete attribute
6. **QR Code**: Properly sized for mobile scanning
7. **Recovery Codes**: Scrollable on small screens

### Testing Strategy

#### Unit Tests
- Component rendering
- Form validation
- State management
- API client functions
- Hook behavior

#### Integration Tests
- Complete setup flows
- Login with 2FA
- Recovery code usage
- Trusted device management
- Error scenarios

#### E2E Tests
- Full user journey (signup → setup → login)
- QR code scanning (with mock authenticator)
- Multi-device scenarios
- Error recovery paths

### Security Considerations

1. **Partial Token**: Limited scope, short expiration
2. **Device ID Storage**: localStorage with fallback
3. **Code Input**: Clear on error, no autocomplete
4. **Recovery Codes**: Warn about saving securely
5. **Trusted Devices**: Clear explanation of risks
6. **HTTPS Only**: Enforce secure connections
7. **No Code Logging**: Never log verification codes
8. **Session Management**: Clear sensitive data on logout

### Performance Optimizations

1. **Code Splitting**: Lazy load 2FA module
2. **Image Optimization**: Optimized QR code size
3. **Prefetching**: Prefetch 2FA assets on login page
4. **Memoization**: Memo expensive components
5. **Debouncing**: Debounce resend requests
6. **React Query**: Proper caching strategy
7. **Bundle Size**: Minimize dependencies

## Consequences

### Positive

1. **Consistent Architecture**: Follows existing patterns in codebase
2. **Type Safety**: Full TypeScript coverage
3. **State Management**: TanStack Store for predictable state
4. **Server State**: TanStack Query for efficient caching
5. **Form Handling**: TanStack Form for validation
6. **Developer Experience**: Excellent DX with TanStack DevTools
7. **Accessibility**: Built-in accessible components from Radix UI
8. **Mobile-First**: Responsive design from the start
9. **Modular**: Reusable components and hooks
10. **Maintainable**: Clear separation of concerns

### Negative

1. **Bundle Size**: Additional code for 2FA features (~50-80KB)
2. **Complexity**: More states to manage during auth flow
3. **Testing Overhead**: More flows to test
4. **Learning Curve**: Users need to understand 2FA
5. **Support Burden**: More user assistance needed
6. **Device Management**: Users may lose trusted devices
7. **Recovery Codes**: Users may lose codes

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Users lose authenticator | Recovery codes prominently displayed |
| QR code won't scan | Provide manual secret entry |
| Browser clears localStorage | Device trust via cookies as fallback |
| Partial token expires | Clear messaging + redirect to login |
| Network failure during setup | Save progress + resume capability |
| Accessibility issues | Regular a11y audits + testing |
| Mobile UX problems | Mobile-first design + testing |
| Complex user flows | User testing + iterative improvements |

## Implementation Plan

### Phase 1: Core Infrastructure (4-6 hours)
- [ ] Create twofa module structure
- [ ] Implement API client functions
- [ ] Create TypeScript types
- [ ] Set up TanStack Store
- [ ] Create base hooks with React Query
- [ ] Unit tests for client and hooks

### Phase 2: Components (6-8 hours)
- [ ] VerificationInput component
- [ ] QRCodeDisplay component
- [ ] RecoveryCodeList component
- [ ] TotpSetup component
- [ ] EmailSetup component
- [ ] SmsSetup component
- [ ] RememberDeviceCheckbox component
- [ ] TrustedDeviceList component
- [ ] Component tests

### Phase 3: Routes & Pages (8-10 hours)
- [ ] 2FA setup page (routes.2fa-setup.tsx)
- [ ] 2FA verification page (routes.2fa-verify.tsx)
- [ ] 2FA settings page (routes.2fa-settings.tsx)
- [ ] Recovery codes page (routes.recovery-codes.tsx)
- [ ] Trusted devices page (routes.trusted-devices.tsx)
- [ ] Route integration tests

### Phase 4: Login Integration (4-6 hours)
- [ ] Modify useLogin hook for 2FA flow
- [ ] Add device_id handling
- [ ] Update login page UI
- [ ] Handle redirect after verification
- [ ] Integration tests

### Phase 5: Polish & Testing (4-6 hours)
- [ ] Error handling refinement
- [ ] Loading states
- [ ] Responsive design testing
- [ ] Accessibility audit
- [ ] Mobile testing
- [ ] E2E tests
- [ ] User acceptance testing

### Phase 6: Documentation (2-3 hours)
- [ ] User guide for 2FA setup
- [ ] Developer documentation
- [ ] API documentation
- [ ] Troubleshooting guide

**Total Estimated Time: 28-39 hours**

## Alternatives Considered

### 1. Context API Instead of TanStack Store
**Pros**: Built-in, no dependency
**Cons**: More boilerplate, less DevTools support
**Decision**: ✅ Rejected - TanStack Store already in use

### 2. Redux for State Management
**Pros**: Mature, well-tested
**Cons**: More boilerplate, heavier bundle
**Decision**: ✅ Rejected - TanStack ecosystem preferred

### 3. React Hook Form Instead of TanStack Form
**Pros**: Popular, feature-rich
**Cons**: Different API, already using TanStack Form
**Decision**: ✅ Rejected - Maintain consistency

### 4. Custom API Client Instead of Extending Existing
**Pros**: More flexibility
**Cons**: Code duplication, inconsistency
**Decision**: ✅ Rejected - Extend existing client

### 5. Modal-Based Setup Instead of Pages
**Pros**: Less navigation
**Cons**: Less mobile-friendly, harder to bookmark
**Decision**: ✅ Partially Accepted - Use modals for quick actions, pages for setup

### 6. Inline 2FA on Login Page
**Pros**: Fewer page transitions
**Cons**: Complex conditional rendering, poor UX
**Decision**: ✅ Rejected - Separate verification page better

## References

- [TanStack Router Documentation](https://tanstack.com/router)
- [TanStack Query Documentation](https://tanstack.com/query)
- [TanStack Form Documentation](https://tanstack.com/form)
- [TanStack Store Documentation](https://tanstack.com/store)
- [Radix UI Documentation](https://www.radix-ui.com/)
- [OWASP 2FA Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ADR-003: 2FA Backend Architecture](./ADR-003-TWO-FACTOR-AUTHENTICATION.md)

## Appendix A: File Structure

```
web/src/modules/twofa/
├── client.ts                        # API client functions (~150 lines)
├── hooks.ts                         # React Query hooks (~200 lines)
├── store.ts                         # TanStack Store (~50 lines)
├── types.ts                         # TypeScript types (~100 lines)
├── routes.2fa-setup.tsx            # Setup page (~250 lines)
├── routes.2fa-verify.tsx           # Verification page (~200 lines)
├── routes.2fa-settings.tsx         # Settings page (~300 lines)
├── routes.recovery-codes.tsx       # Recovery codes page (~150 lines)
├── routes.trusted-devices.tsx      # Trusted devices page (~200 lines)
└── components/
    ├── TotpSetup.tsx               # TOTP setup (~200 lines)
    ├── EmailSetup.tsx              # Email setup (~150 lines)
    ├── SmsSetup.tsx                # SMS setup (~180 lines)
    ├── VerificationInput.tsx       # Code input (~120 lines)
    ├── RecoveryCodeList.tsx        # Display codes (~100 lines)
    ├── TrustedDeviceList.tsx       # Device list (~150 lines)
    ├── QRCodeDisplay.tsx           # QR display (~80 lines)
    └── RememberDeviceCheckbox.tsx  # Checkbox (~50 lines)

Total: ~2,430 lines of TypeScript/React code
```

## Appendix B: API Response Examples

See [ADR-003 Appendix A](./ADR-003-TWO-FACTOR-AUTHENTICATION.md#appendix-a-api-requestresponse-examples) for complete API documentation.

## Appendix C: Component Props & Types

```typescript
// types.ts - Complete type definitions

export type TwoFactorMethod = 'totp' | 'email' | 'sms'

export interface TwoFactorSetupRequest {
  method: TwoFactorMethod
  phone_number?: string
}

export interface TwoFactorSetupResponse {
  method: TwoFactorMethod
  secret?: string
  qr_code?: string
  qr_code_image?: string
  message?: string
  expires_in?: number
}

export interface TwoFactorVerifyRequest {
  code: string
  remember_me?: boolean
}

export interface TwoFactorVerifyResponse {
  tokens: {
    access: string
    refresh: string
  }
  user: {
    id: number
    username: string
    email: string
  }
  device_id?: string
  device_trust_expires?: string
  skipped_2fa?: boolean
  reason?: string
}

export interface TwoFactorStatusResponse {
  is_enabled: boolean
  preferred_method: TwoFactorMethod
  phone_number?: string
  backup_email?: string
  created_at: string
  updated_at: string
}

export interface RecoveryCode {
  code: string
  is_used: boolean
}

export interface TrustedDevice {
  device_id: string
  device_name: string
  ip_address: string
  last_used_at: string
  expires_at: string
  created_at: string
}

// Component Props
export interface VerificationInputProps {
  length?: number
  value: string
  onChange: (value: string) => void
  onComplete?: (value: string) => void
  autoFocus?: boolean
}

export interface TotpSetupProps {
  onComplete?: () => void
  onCancel?: () => void
}

export interface QRCodeDisplayProps {
  qrCode: string
  secret: string
  showManualEntry?: boolean
}

export interface RecoveryCodeListProps {
  codes: string[]
  showDownloadButton?: boolean
}

export interface TrustedDeviceListProps {
  devices: TrustedDevice[]
  onRemove?: (deviceId: string) => void
}
```

## Appendix D: Styling Guidelines

```css
/* 2FA specific styles following Tailwind conventions */

/* Verification Input */
.verification-input {
  @apply w-12 h-12 text-center text-2xl;
  @apply border-2 border-gray-300 rounded-lg;
  @apply focus:border-blue-500 focus:ring-2 focus:ring-blue-200;
  @apply transition-all;
}

/* QR Code Container */
.qr-code-container {
  @apply bg-white p-6 rounded-lg shadow-md;
  @apply border-2 border-gray-200;
}

/* Recovery Code */
.recovery-code {
  @apply font-mono text-lg;
  @apply bg-gray-100 p-3 rounded;
  @apply select-all cursor-pointer;
  @apply hover:bg-gray-200 transition-colors;
}

/* Trusted Device Card */
.trusted-device-card {
  @apply bg-white p-4 rounded-lg border border-gray-200;
  @apply hover:shadow-md transition-shadow;
}

/* 2FA Status Badge */
.twofa-enabled-badge {
  @apply bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium;
}

.twofa-disabled-badge {
  @apply bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm font-medium;
}
```

---

**Next Steps:**
1. Review and approve this ADR
2. Create GitHub issue/project for implementation
3. Begin Phase 1 implementation
4. Schedule user testing sessions
5. Plan rollout strategy
