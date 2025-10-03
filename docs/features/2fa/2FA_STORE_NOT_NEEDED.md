# 2FA Implementation: TanStack Store Not Needed

## Summary

**You DON'T need a separate TanStack Store for 2FA.** Use TanStack Router's built-in state passing instead.

## Why?

The 2FA flow only needs to pass temporary data between pages:
- `partialToken` - Only needed during login flow (1-2 pages)
- `method` - Which 2FA method to use (temporary)
- Setup data - QR codes, secrets (wizard flow only)

**None of this needs global state management.**

## Recommended Approach: Router State

TanStack Router already has built-in state passing:

```typescript
// Pass state when navigating
navigate({ 
  to: '/2fa/verify',
  state: { partialToken: 'xxx', method: 'totp' }
})

// Receive state in destination page
const location = useLocation()
const { partialToken, method } = location.state || {}
```

**Benefits:**
- ✅ Built-in to TanStack Router (already using it)
- ✅ No extra dependencies
- ✅ Automatic cleanup when navigating away
- ✅ Type-safe
- ✅ ~80 lines of code saved

## What Still Needs Storage?

| State | Where to Store | Why |
|-------|---------------|-----|
| `accessToken` | `authStore` (existing) | Needed globally |
| `device_id` | `localStorage` | Persistent across sessions |
| `partialToken` | Router state | Temporary (1-2 pages) |
| `method` | Router state | Temporary |
| Setup wizard data | React Query `mutation.data` | Built-in to mutation |

## Updated Module Structure

```
web/src/features/twofa/
├── client.ts              # API functions ✅
├── hooks.ts               # React Query hooks ✅
├── types.ts               # TypeScript types ✅
├── store.ts               # ❌ NOT NEEDED - Delete this
├── routes.2fa-verify.tsx  # Uses router state ✅
├── routes.2fa-setup.tsx   # Uses router state ✅
└── components/            # Regular components ✅
```

## Complete Example

### 1. Login Hook (Pass via Router)

```typescript
// login/hooks.ts
export function useLogin() {
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: (credentials) => api.post('/auth/login/', credentials),
    onSuccess: (data) => {
      if (data.requires_2fa) {
        // Pass state via router - NO STORE NEEDED!
        navigate({ 
          to: '/2fa/verify',
          state: {
            partialToken: data.partial_token,
            method: data.method
          }
        })
      } else {
        setAccessToken(data.tokens.access)
      }
    },
  })
}
```

### 2. Verification Page (Receive via Router)

```typescript
// routes.2fa-verify.tsx
function TwoFactorVerifyPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { partialToken, method } = location.state || {}
  
  // Redirect if accessed directly without state
  if (!partialToken || !method) {
    return <Navigate to="/login" />
  }
  
  const verify = useVerify2FA(partialToken)
  const [code, setCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  
  return (
    <div className="max-w-md mx-auto p-6">
      <h1>Enter code from your {method}</h1>
      
      <VerificationInput
        value={code}
        onChange={setCode}
        onComplete={(c) => verify.mutate({ code: c, remember_me: rememberMe })}
      />
      
      <Checkbox
        checked={rememberMe}
        onChange={setRememberMe}
        label="Remember this device for 30 days"
      />
      
      <Button
        onClick={() => verify.mutate({ code, remember_me: rememberMe })}
        disabled={code.length !== 6 || verify.isPending}
      >
        {verify.isPending ? 'Verifying...' : 'Verify'}
      </Button>
      
      {verify.error && (
        <p className="text-red-600">{verify.error.message}</p>
      )}
    </div>
  )
}
```

### 3. Verify Hook (Takes Token as Parameter)

```typescript
// twofa/hooks.ts
export function useVerify2FA(partialToken: string) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: ({ code, remember_me }: { code: string; remember_me?: boolean }) => {
      // Use the partial token passed as parameter
      return fetch(`${API_BASE}/auth/2fa/verify/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${partialToken}`,
        },
        body: JSON.stringify({ code, remember_me }),
      }).then(res => {
        if (!res.ok) throw new Error('Invalid code')
        return res.json()
      })
    },
    onSuccess: (data) => {
      // Store access token in existing authStore
      setAccessToken(data.tokens.access)
      
      // Store device_id if provided
      if (data.device_id) {
        localStorage.setItem('device_id', data.device_id)
      }
      
      // Invalidate and navigate
      queryClient.invalidateQueries({ queryKey: ['user'] })
      navigate({ to: '/' })
    },
  })
}
```

## Setup Flow Example

Setup flows also work without a store:

```typescript
function TotpSetup({ onComplete }: { onComplete?: () => void }) {
  const [step, setStep] = useState<'init' | 'scan' | 'verify' | 'codes'>('init')
  const initSetup = useInitialize2FASetup()
  const verifySetup = useVerify2FASetup()
  
  // React Query automatically caches mutation data!
  const setupData = initSetup.data
  const recoveryCodes = verifySetup.data?.recovery_codes
  
  if (step === 'init') {
    return (
      <Button onClick={() => {
        initSetup.mutate({ method: 'totp' })
        setStep('scan')
      }}>
        Start Setup
      </Button>
    )
  }
  
  if (step === 'scan' && setupData) {
    return (
      <div>
        <QRCodeDisplay 
          qrCode={setupData.qr_code_image} 
          secret={setupData.secret} 
        />
        <Button onClick={() => setStep('verify')}>Next</Button>
      </div>
    )
  }
  
  if (step === 'verify') {
    return (
      <div>
        <VerificationInput
          onComplete={(code) => {
            verifySetup.mutate({ code })
            setStep('codes')
          }}
        />
      </div>
    )
  }
  
  if (step === 'codes' && recoveryCodes) {
    return (
      <div>
        <RecoveryCodeList codes={recoveryCodes} />
        <Button onClick={onComplete}>Done</Button>
      </div>
    )
  }
  
  // No store needed - just React Query mutation data + local state!
}
```

## Benefits of This Approach

### Simpler
- ~80 lines of code removed (no store.ts file)
- No manual state cleanup
- No store imports/exports
- Less to test

### More Idiomatic
- Router state is designed for this use case
- React Query mutation data is designed for API responses
- Following React/Router patterns

### Auto-Cleanup
- Router state cleared when navigating away
- React Query mutation data cleared on component unmount
- No manual cleanup needed

### Type-Safe
```typescript
// Can type the router state
interface TwoFactorVerifyState {
  partialToken: string
  method: 'totp' | 'email' | 'sms'
}

const { partialToken, method } = location.state as TwoFactorVerifyState
```

## When to Use TanStack Store

Only use TanStack Store for:
- ✅ Global state needed across many components
- ✅ State that persists across navigation
- ✅ State that needs complex logic/middleware

**The 2FA flow doesn't need any of these.**

## Comparison: With vs Without Store

### WITH Store (Current ADR) - ❌ More Complex

```typescript
// Need to create store
const twoFactorStore = new Store({ partialToken: null, method: null })

// Set in login
setPartialToken(data.partial_token)
setTwoFactorMethod(data.method)

// Get in verify page
const { partialToken, method } = useStore(twoFactorStore)

// Clean up after
clearTwoFactorState()
```

### WITHOUT Store (Recommended) - ✅ Simpler

```typescript
// Pass in login
navigate({ to: '/2fa/verify', state: { partialToken, method } })

// Get in verify page
const { partialToken, method } = location.state

// Cleanup automatic when navigating away
```

**Literally 80% less code for the same functionality.**

## Decision

**Recommendation: Remove `twofa/store.ts` from ADR-004**

Update the ADR to use:
1. Router state for navigation-based data
2. React Query mutation.data for API responses
3. Keep existing authStore for global access token
4. localStorage for device_id (persistent)

## Implementation Checklist

- [ ] Remove `store.ts` from module structure in ADR
- [ ] Update hooks to take parameters instead of reading from store
- [ ] Update examples to use router state
- [ ] Update verification page to use `location.state`
- [ ] Update setup components to use mutation data
- [ ] Update timeline (save ~2 hours by removing store implementation)

---

**Last Updated:** 2025-01-08  
**Status:** Recommended Simplification
