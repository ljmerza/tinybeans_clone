# Refresh Token Flow - Before & After

## 🔴 BEFORE (Problem)

### Issue 1: Duplicate Refresh Calls

```
Page Refresh
    │
    ├──> AppBootstrap useEffect() ──> authClient.refreshAccessToken()
    │                                       │
    │                                       └──> POST /auth/token/refresh/  (Call #1)
    │
    └──> AppBootstrap useEffect() ──> authClient.refreshAccessToken()  (StrictMode double-mount)
         (runs again in dev)                  │
                                              └──> POST /auth/token/refresh/  (Call #2) ❌
```

### Issue 2: Race Condition

```
Timeline:
0ms   AppBootstrap starts
      └──> Status: "loading"
      └──> Calls refreshAccessToken() (async)

1ms   AppBootstrap renders children immediately
      └──> AppProviders rendered with isInitializing=false
           └──> AuthSessionProvider checks: accessToken=null ❌
                └──> Sets status to "guest" (WRONG!)

50ms  refreshAccessToken() completes successfully
      └──> Sets accessToken="abc123..." ✅
      └──> But UI already rendered as "guest" ❌
```

## ✅ AFTER (Solution)

### Fix 1: Centralized Deduplication

```
Page Refresh
    │
    ├──> Call 1: refreshAccessToken()
    │         │
    │         └──> Creates refreshPromise ──> POST /auth/token/refresh/ ✅
    │
    └──> Call 2: refreshAccessToken()  (StrictMode or concurrent)
              │
              └──> Returns existing refreshPromise (no duplicate call!) ✅
```

### Fix 2: Proper Initialization State

```
Timeline:
0ms   AppBootstrap starts
      └──> Status: "loading"
      └──> Shows <LoadingPage />
      └──> Calls refreshAccessToken() (async)

50ms  refreshAccessToken() completes
      └──> Sets accessToken="abc123..." ✅
      └──> Sets status: "ready"

51ms  AppBootstrap renders AppProviders
      └──> AuthSessionProvider checks: accessToken="abc123..." ✅
           └──> Sets status to "authenticated" ✅
           └──> UI shows correct logged-in state ✅
```

## Key Implementation Details

### Deduplication Pattern
```typescript
// Module-level promise tracker
let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  // Return existing promise if refresh already in progress
  if (refreshPromise) {
    return refreshPromise;
  }
  
  // Create new promise and cache it
  refreshPromise = (async () => {
    try {
      // ... actual refresh logic
    } finally {
      // Clear cache after completion
      refreshPromise = null;
    }
  })();
  
  return refreshPromise;
}
```

### Bootstrap Flow
```typescript
export function AppBootstrap({ queryClient }: AppBootstrapProps) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  
  useEffect(() => {
    async function bootstrap() {
      await ensureCsrfToken();
      await refreshAccessToken();  // Wait for completion
      setStatus("ready");  // Only then set ready
    }
    bootstrap();
  }, []);
  
  if (status === "loading") {
    return <LoadingPage />;  // Block rendering until ready
  }
  
  return <AppProviders isInitializing={false} />;  // Only render when ready
}
```

## Benefits

✅ **No duplicate API calls** - Saves bandwidth and prevents race conditions  
✅ **Correct UI state** - Shows authenticated UI when user is logged in  
✅ **Works with StrictMode** - Handles React's double-mounting in development  
✅ **Single source of truth** - One refresh function shared across all clients  
✅ **Proper async handling** - Waits for initialization before rendering UI
