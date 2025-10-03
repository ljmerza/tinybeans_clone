# TanStack Query vs TanStack Store - When to Use Each

## Quick Answer

**TanStack Query** and **TanStack Store** serve different purposes and work together:

- **TanStack Query** = Server state (data from APIs)
- **TanStack Store** = Client state (UI state, local data)

## Real Example from Your Codebase

Your current `login` module already uses this pattern:

```typescript
// web/src/features/auth/store.ts
// ✅ TanStack Store: Stores the ACCESS TOKEN (client state)
export const authStore = new Store({
  accessToken: null as string | null,
})

// web/src/features/auth/hooks.ts
// ✅ TanStack Query: Manages API calls and USER DATA (server state)
export function useLogin() {
  return useMutation({
    mutationFn: (credentials) => api.post('/auth/login/', credentials),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access)  // Store in TanStack Store
    },
  })
}

export function useMe() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => api.get('/users/me/'),  // Fetches from server
    staleTime: 5 * 60 * 1000,              // Caches for 5 minutes
  })
}
```

## The Difference

### TanStack Query (Server State)
**Purpose:** Manage data from the server

**Use for:**
- API calls (GET, POST, PUT, DELETE)
- Caching server data
- Loading states for API requests
- Error handling for API failures
- Automatic refetching
- Optimistic updates
- Data synchronization

**Examples in 2FA:**
```typescript
// ✅ USE TANSTACK QUERY for API calls
export function useVerify2FA() {
  return useMutation({
    mutationFn: (code) => api.post('/auth/2fa/verify/', { code }),
    // Automatic loading/error states
    // Caching strategy
    // Retry logic
  })
}

export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa', 'status'],
    queryFn: () => api.get('/auth/2fa/status/'),
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  })
}
```

**What it provides:**
- `data` - The server response
- `isLoading` - Is the request in progress?
- `isError` - Did the request fail?
- `error` - Error details
- `refetch()` - Manually refetch
- Automatic caching and invalidation

---

### TanStack Store (Client State)
**Purpose:** Manage local UI state that doesn't come from the server

**Use for:**
- Tokens (access token, partial token)
- UI state (modals open/closed, active tab)
- Form state (before submission)
- Temporary data (wizard step, draft data)
- Settings that don't need server sync

**Examples in 2FA:**
```typescript
// ✅ USE TANSTACK STORE for client-only state
export const twoFactorStore = new Store({
  partialToken: null,        // Not from API, set during login
  method: null,              // Current 2FA method being used
  requiresVerification: false, // UI state
  setupInProgress: false,    // Wizard state
})
```

**What it provides:**
- Simple state container
- No automatic API calls
- No caching strategy
- Just local state management

---

## When to Use Each

### Use TanStack Query When:
- ✅ Making API calls
- ✅ Need caching
- ✅ Need loading/error states
- ✅ Data comes from server
- ✅ Need automatic refetching
- ✅ Need optimistic updates

### Use TanStack Store When:
- ✅ Storing tokens
- ✅ UI state (modal open/closed)
- ✅ Temporary wizard/form data
- ✅ Data that never goes to server
- ✅ Simple client-side state

---

## 2FA Example - Both Working Together

Here's how they work together in the 2FA flow:

```typescript
// ========================================
// 1. LOGIN - Store partial token in TanStack Store
// ========================================
export function useLogin() {
  return useMutation({
    // TanStack Query handles the API call
    mutationFn: (credentials) => api.post('/auth/login/', credentials),
    
    onSuccess: (data) => {
      if (data.requires_2fa) {
        // TanStack Store stores the client state
        setPartialToken(data.partial_token)
        setTwoFactorMethod(data.method)
        setRequiresVerification(true)
      }
    },
  })
}

// ========================================
// 2. VERIFY - Use partial token from Store
// ========================================
export function useVerify2FA() {
  return useMutation({
    // TanStack Query handles the API call
    mutationFn: ({ code, remember_me }) => {
      // Read from TanStack Store
      const { partialToken } = twoFactorStore.state
      
      // Make API call with TanStack Query
      return api.post('/auth/2fa/verify/', { code, remember_me }, {
        headers: { Authorization: `Bearer ${partialToken}` }
      })
    },
    
    onSuccess: (data) => {
      // Store new token in TanStack Store
      setAccessToken(data.tokens.access)
      
      // Clear temporary state in TanStack Store
      clearTwoFactorState()
    },
  })
}

// ========================================
// 3. GET STATUS - Pure TanStack Query
// ========================================
export function use2FAStatus() {
  return useQuery({
    // No TanStack Store needed - just fetching from server
    queryKey: ['2fa', 'status'],
    queryFn: () => api.get('/auth/2fa/status/'),
  })
}

// Component usage:
function TwoFactorVerify() {
  // TanStack Query - manages API state
  const verify = useVerify2FA()
  
  // TanStack Store - manages local UI state
  const { method, partialToken } = useStore(twoFactorStore)
  
  return (
    <div>
      {/* TanStack Query provides loading/error states */}
      {verify.isLoading && <Spinner />}
      {verify.isError && <Error message={verify.error.message} />}
      
      {/* TanStack Store provides local state */}
      <p>Method: {method}</p>
      
      <button onClick={() => verify.mutate({ code: '123456' })}>
        Verify
      </button>
    </div>
  )
}
```

---

## Why Not Use Only TanStack Query?

You *could* use TanStack Query for everything, but it's overkill:

```typescript
// ❌ BAD: Using Query for client-only state
const { data: modalOpen } = useQuery({
  queryKey: ['ui', 'modalOpen'],
  queryFn: () => false, // This is weird - not fetching from server!
  staleTime: Infinity,
})

// ✅ GOOD: Use Store for client state
const uiStore = new Store({ modalOpen: false })
```

**Problems with using Query for everything:**
- Unnecessary complexity for simple state
- Caching strategies don't make sense for UI state
- Loading states are confusing for instant local state
- Query keys for non-server data is awkward

---

## Why Not Use Only TanStack Store?

You *could* use TanStack Store for everything, but you lose benefits:

```typescript
// ❌ BAD: Manually managing server state
const dataStore = new Store({ userData: null, loading: false, error: null })

async function fetchUser() {
  dataStore.setState({ loading: true })
  try {
    const data = await api.get('/users/me/')
    dataStore.setState({ userData: data, loading: false })
  } catch (error) {
    dataStore.setState({ error, loading: false })
  }
}

// ✅ GOOD: Use Query for server state
const { data, isLoading, isError } = useQuery({
  queryKey: ['user'],
  queryFn: () => api.get('/users/me/'),
  staleTime: 5 * 60 * 1000, // Automatic caching!
})
```

**Problems with using Store for server state:**
- No automatic caching
- No automatic refetching
- No deduplication (multiple requests for same data)
- Manual loading/error state management
- No retry logic
- No optimistic updates
- Reinventing the wheel

---

## Summary - The Perfect Combo

```
┌─────────────────────────────────────────────────────────┐
│                  Your React Component                   │
│                                                          │
│  ┌──────────────────────┐    ┌───────────────────────┐ │
│  │   TanStack Query     │    │   TanStack Store      │ │
│  │                      │    │                       │ │
│  │  • User data         │    │  • Access token       │ │
│  │  • 2FA status        │    │  • Partial token      │ │
│  │  • Recovery codes    │    │  • UI state           │ │
│  │  • Trusted devices   │    │  • Wizard step        │ │
│  │                      │    │  • Current method     │ │
│  │  (from server)       │    │  (local only)         │ │
│  └──────────────────────┘    └───────────────────────┘ │
│           ↓                              ↓              │
│      [API calls]                  [Local state]         │
└─────────────────────────────────────────────────────────┘
```

**Golden Rule:**
- If it comes from the server → **TanStack Query**
- If it's local to the browser → **TanStack Store**

---

## Practical 2FA Example

```typescript
// twofa/store.ts
// ✅ Client state only
export const twoFactorStore = new Store({
  partialToken: null,           // Temporary token during login
  method: null,                 // Which method user is using
  requiresVerification: false,  // Should show verification page?
  setupInProgress: false,       // Is setup wizard running?
})

// twofa/hooks.ts
// ✅ Server state - API calls
export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa', 'status'],
    queryFn: () => api.get('/auth/2fa/status/'),
  })
}

export function useVerify2FA() {
  return useMutation({
    mutationFn: ({ code, remember_me }) => 
      api.post('/auth/2fa/verify/', { code, remember_me }),
  })
}

export function useTrustedDevices() {
  return useQuery({
    queryKey: ['2fa', 'trusted-devices'],
    queryFn: () => api.get('/auth/2fa/trusted-devices/'),
  })
}
```

---

## Updated ADR Recommendation

Based on this understanding, the ADR is correct as-is. Here's why we need both:

### TanStack Query in 2FA:
- API calls (setup, verify, disable)
- Fetch 2FA status from server
- Get trusted devices list
- Generate recovery codes
- All server data with caching

### TanStack Store in 2FA:
- Store partial token during login flow
- Track which method user selected
- Remember wizard step
- UI state (modal open, current tab)
- Temporary data before API submission

They complement each other perfectly! 🎯

---

## Conclusion

**Both are needed** because they solve different problems:

| Feature | TanStack Query | TanStack Store |
|---------|----------------|----------------|
| Purpose | Server state | Client state |
| Caching | ✅ Yes | ❌ No |
| Loading states | ✅ Automatic | ❌ Manual |
| Error handling | ✅ Built-in | ❌ Manual |
| API calls | ✅ Perfect for this | ❌ Not designed for this |
| Simple state | ⚠️ Overkill | ✅ Perfect for this |
| Tokens/UI state | ⚠️ Awkward | ✅ Natural fit |

**Your codebase already uses this pattern correctly!** The ADR follows the same approach. 👍
