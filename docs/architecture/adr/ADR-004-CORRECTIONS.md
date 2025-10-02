# ADR-004 Addendum: Backend Endpoints Review & Corrections

**Date:** 2025-01-08  
**Status:** Corrections Required

## Summary

After reviewing the actual Django backend implementation, several discrepancies were found between the proposed ADR-004 endpoints and the actual backend API. This document outlines the corrections needed.

## Key Findings

### ✅ Endpoints That Match
- `POST /auth/2fa/setup/`
- `POST /auth/2fa/verify-setup/`
- `GET /auth/2fa/status/`
- `POST /auth/2fa/disable/`
- `POST /auth/2fa/recovery-codes/generate/`
- `GET /auth/2fa/recovery-codes/download/`
- `GET /auth/2fa/trusted-devices/`

### ❌ Endpoints That Need Correction

1. **Verify Endpoint**
   - ❌ ADR Proposed: `POST /auth/2fa/verify/`
   - ✅ Backend Actual: `POST /auth/2fa/verify-login/`
   
2. **Resend Code** 
   - ❌ ADR Proposed: `POST /auth/2fa/send-code/`
   - ✅ Backend Actual: **Not implemented** (codes auto-sent during login/setup)
   
3. **Recovery Code Verification**
   - ❌ ADR Proposed: `POST /auth/2fa/recovery-codes/verify/`
   - ✅ Backend Actual: **Merged into** `/auth/2fa/verify-login/` (accepts both codes)
   
4. **Trusted Device Removal**
   - ❌ ADR Proposed: `POST /auth/2fa/trusted-devices/remove/`
   - ✅ Backend Actual: `DELETE /auth/2fa/trusted-devices/<device_id>/`

5. **Partial Token Handling**
   - ❌ ADR Proposed: Partial token in `Authorization` header
   - ✅ Backend Actual: Partial token in request body

## Complete Corrected API Reference

### 1. API Client (Updated)

```typescript
// twofa/client.ts
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

export interface TwoFactorVerifyLoginResponse {
  user: {
    id: number
    username: string
    email: string
  }
  tokens: {
    access: string
    // refresh in HTTP-only cookie
  }
  trusted_device: boolean
}

export interface RecoveryCodesResponse {
  recovery_codes: string[]
  message: string
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

  // Verification (CORRECTED - uses verify-login, not verify)
  verifyLogin: (partial_token: string, code: string, remember_me: boolean = false) =>
    api.post<TwoFactorVerifyLoginResponse>('/auth/2fa/verify-login/', { 
      partial_token,  // ✅ In body, not Authorization header
      code,           // ✅ Can be 6-digit code OR recovery code (XXXX-XXXX-XXXX)
      remember_me 
    }),

  // Disable
  disable: (code: string) =>
    api.post<{ enabled: boolean; message: string }>('/auth/2fa/disable/', { code }),

  // Recovery Codes
  generateRecoveryCodes: () =>
    api.post<RecoveryCodesResponse>('/auth/2fa/recovery-codes/generate/', {}),

  downloadRecoveryCodes: (format: 'txt' | 'pdf') => {
    const url = `${import.meta.env.VITE_API_BASE}/auth/2fa/recovery-codes/download/?format=${format}`
    window.open(url, '_blank')
  },

  // Trusted Devices (CORRECTED - uses DELETE method)
  getTrustedDevices: () =>
    api.get<{ devices: TrustedDevice[] }>('/auth/2fa/trusted-devices/'),

  removeTrustedDevice: (device_id: string) =>
    // ✅ DELETE method with device_id in URL
    fetch(`${import.meta.env.VITE_API_BASE}/auth/2fa/trusted-devices/${device_id}/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        'Authorization': `Bearer ${authStore.state.accessToken}`,
      }
    }).then(r => r.json()),

  // Alternative: DELETE with device_id in body (both work)
  removeTrustedDeviceAlt: (device_id: string) =>
    fetch(`${import.meta.env.VITE_API_BASE}/auth/2fa/trusted-devices/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.state.accessToken}`,
      },
      body: JSON.stringify({ device_id })
    }).then(r => r.json()),
}
```

### 2. React Query Hooks (Updated)

```typescript
// twofa/hooks.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { twoFactorApi } from './client'
import { setAccessToken } from '../login/store'

// Setup hooks
export function useInitialize2FASetup() {
  return useMutation({
    mutationFn: ({ method, phone_number }: { method: 'totp' | 'email' | 'sms'; phone_number?: string }) =>
      twoFactorApi.initializeSetup(method, phone_number),
  })
}

export function useVerify2FASetup() {
  return useMutation({
    mutationFn: (code: string) => twoFactorApi.verifySetup(code),
  })
}

// Status hook
export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa', 'status'],
    queryFn: () => twoFactorApi.getStatus(),
  })
}

// Verification hook (CORRECTED)
export function useVerify2FALogin() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: ({ 
      partial_token, 
      code, 
      remember_me 
    }: { 
      partial_token: string
      code: string
      remember_me?: boolean 
    }) =>
      twoFactorApi.verifyLogin(partial_token, code, remember_me),
    onSuccess: (data) => {
      // Store access token
      setAccessToken(data.tokens.access)
      
      // Device ID cookie is set by backend automatically
      
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['user'] })
      
      // Navigate to home
      navigate({ to: '/' })
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

// Trusted devices hooks (CORRECTED)
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

// Note: No separate "resend code" hook - codes are auto-sent by backend
```

### 3. Enhanced Login Hook (Updated)

```typescript
// login/hooks.ts (modifications)
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { api } from './client'
import { setAccessToken } from './store'

export function useLogin() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: (credentials: { username: string; password: string }) =>
      api.post('/auth/login/', credentials),
    onSuccess: (data: any) => {
      // Check if 2FA is required
      if (data.requires_2fa) {
        // Navigate to 2FA verification with partial token via router state
        navigate({ 
          to: '/2fa/verify',
          state: {
            partialToken: data.partial_token,  // ✅ From response body
            method: data.method,
            message: data.message
          }
        })
      } else {
        // Normal login without 2FA
        setAccessToken(data.tokens.access)
        navigate({ to: '/' })
      }
    },
  })
}
```

### 4. Verification Page Component (Updated)

```typescript
// routes.2fa-verify.tsx
import { createRoute, useNavigate, useLocation, Navigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useVerify2FALogin } from './hooks'
import { VerificationInput } from './components/VerificationInput'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

function TwoFactorVerifyPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { partialToken, method, message } = location.state || {}
  
  const [code, setCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [useRecoveryCode, setUseRecoveryCode] = useState(false)

  const verify = useVerify2FALogin()

  // Redirect if no partial token (direct access)
  if (!partialToken || !method) {
    return <Navigate to="/login" />
  }

  const handleVerify = () => {
    verify.mutate({
      partial_token: partialToken,  // ✅ From router state
      code,                         // ✅ Can be 6-digit OR recovery code
      remember_me: rememberMe
    })
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
      
      {!useRecoveryCode && message && (
        <p className="text-gray-600 mb-6">{message}</p>
      )}
      
      {!useRecoveryCode && !message && (
        <p className="text-gray-600 mb-6">
          Enter the code from your {getMethodDisplay()}
        </p>
      )}

      {useRecoveryCode && (
        <p className="text-gray-600 mb-6">
          Enter one of your recovery codes (format: XXXX-XXXX-XXXX)
        </p>
      )}

      <div className="space-y-6">
        {!useRecoveryCode && (
          <VerificationInput
            length={6}
            value={code}
            onChange={setCode}
            onComplete={handleVerify}
          />
        )}
        
        {useRecoveryCode && (
          <input
            type="text"
            placeholder="XXXX-XXXX-XXXX"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full p-2 border rounded"
            maxLength={14}
          />
        )}

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
          disabled={code.length < (useRecoveryCode ? 14 : 6) || verify.isPending}
          className="w-full"
        >
          {verify.isPending ? 'Verifying...' : 'Verify'}
        </Button>

        {verify.error && (
          <p className="text-sm text-red-600 text-center">
            {(verify.error as any)?.message || 'Invalid code'}
          </p>
        )}

        {/* Note: No resend button - backend auto-sends codes */}

        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setUseRecoveryCode(!useRecoveryCode)
              setCode('')
            }}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {useRecoveryCode ? 'Use verification code' : 'Use recovery code instead'}
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

### 5. Trusted Devices Management (Updated)

```typescript
// routes.trusted-devices.tsx
import { useTrustedDevices, useRemoveTrustedDevice } from '../hooks'
import { Button } from '@/components/ui/button'

function TrustedDevicesPage() {
  const { data, isLoading } = useTrustedDevices()
  const removeDevice = useRemoveTrustedDevice()

  const handleRemove = (device_id: string) => {
    if (confirm('Remove this trusted device? You\'ll need to verify with 2FA next time you login from it.')) {
      removeDevice.mutate(device_id)
    }
  }

  if (isLoading) return <div>Loading...</div>

  const devices = data?.devices || []

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Trusted Devices</h1>
      
      {devices.length === 0 && (
        <p className="text-gray-600">No trusted devices</p>
      )}

      <div className="space-y-4">
        {devices.map((device) => (
          <div 
            key={device.device_id} 
            className="border rounded p-4 flex justify-between items-start"
          >
            <div>
              <h3 className="font-semibold">{device.device_name}</h3>
              <p className="text-sm text-gray-600">IP: {device.ip_address}</p>
              <p className="text-sm text-gray-600">
                Last used: {new Date(device.last_used_at).toLocaleString()}
              </p>
              <p className="text-sm text-gray-600">
                Expires: {new Date(device.expires_at).toLocaleString()}
              </p>
            </div>
            
            <Button
              variant="destructive"
              size="sm"
              onClick={() => handleRemove(device.device_id)}
              disabled={removeDevice.isPending}
            >
              Remove
            </Button>
          </div>
        ))}
      </div>
    </div>
  )
}
```

## Additional Backend Endpoints (Optional)

The backend also has these auth endpoints that could be documented in the frontend:

### Email Verification
```typescript
export const emailApi = {
  resendVerification: (email: string) =>
    api.post('/auth/verify-email/resend/', { email }),
  
  confirmEmail: (token: string) =>
    api.post('/auth/verify-email/confirm/', { token }),
}
```

### Password Management
```typescript
export const passwordApi = {
  change: (current_password: string, password: string) =>
    api.post('/auth/password/change/', { current_password, password }),
  
  requestReset: (email: string) =>
    api.post('/auth/password/reset/request/', { email }),
  
  confirmReset: (token: string, password: string) =>
    api.post('/auth/password/reset/confirm/', { token, password }),
}
```

## Summary of Corrections

### Must Fix (Breaking Changes)
1. ✅ Rename `/auth/2fa/verify/` → `/auth/2fa/verify-login/`
2. ✅ Remove `/auth/2fa/send-code/` endpoint (not implemented)
3. ✅ Remove `/auth/2fa/recovery-codes/verify/` (merged into verify-login)
4. ✅ Change `POST /auth/2fa/trusted-devices/remove/` → `DELETE /auth/2fa/trusted-devices/<id>/`
5. ✅ Update partial token to be in request body, not Authorization header
6. ✅ Document that verify-login accepts both 6-digit codes and recovery codes

### Should Fix (Enhancements)
7. 📋 Remove "resend code" functionality (auto-sent by backend)
8. 📋 Document that device_id cookie is set by backend automatically
9. 📋 Add note that recovery codes work in single verify-login endpoint

### Optional (Nice to Have)
10. 📋 Add email verification endpoints
11. 📋 Add password management endpoints
12. 📋 Document trusted_device response flag from verify-login

## Impact Assessment

**Low Risk:**
- Endpoint names and HTTP methods are implementation details
- No breaking changes to user flows
- All functionality is still supported

**Recommendation:**
- Update ADR-004 with corrections
- Implement frontend with corrected endpoints
- Add note about backend API matching

---

**Next Steps:**
1. Update ADR-004 with corrected endpoints
2. Update all code examples in ADR
3. Remove TanStack Store for 2FA (use router state)
4. Optionally add password management endpoints for completeness

