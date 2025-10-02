# Auth (Login/Signup) Planning for the Web App

This document outlines how to build login and signup pages in the `web` app using:
- TanStack Router (routing, navigation, route guards)
- TanStack Query (server state, auth mutations, user query)
- TanStack React Form (form state + validation)
- shadcn/ui + Tailwind CSS (UI components/styles)
- Django app API (session or JWT based)

The goal is to provide a clean, accessible UI and a robust client-side auth flow that integrates cleanly with the Django backend.

## Backend: Django users app auth model

The current backend uses JWT via djangorestframework-simplejwt with this behavior:
- Access token is returned in the response body
- Refresh token is stored in an HTTP-only cookie (name: refresh_token)
- The cookie path is /api/auth/token/refresh/

Endpoints (all under /api/users/):
- POST auth/signup/ -> { user, tokens: { access } } and sets refresh cookie
  - Request body: { username, email, password }
- POST auth/login/ -> { user, tokens: { access } } and sets refresh cookie
  - Request body: { username, password }
- POST auth/token/refresh/ -> { access } and rotates refresh cookie
  - Uses only the HTTP-only cookie; no request body required
- GET  me/ -> { user } (requires Authorization: Bearer <access>)

Notes
- There is no logout endpoint. “Logout” on the client means clearing the in-memory access token. The refresh cookie will remain until expiry; users will be issued a new access token if the client calls refresh again.
- Email verification exists: verify-email/resend/ and verify-email/confirm/. Verification tokens are delivered by email only.


## Packages and project wiring

- QueryClient and RouterProvider are already in the project. Ensure the following baseline in src/main.tsx:
  - QueryClient with proper default options (retry: false for auth mutations)
  - React Query Devtools conditionally
  - Router (TanStack Router v1)
- Use an auth client that adds Authorization: Bearer <access> and includes credentials for the refresh cookie.

## Directory and route map

## Frontend plumbing

- API base and dev proxy
  - Use VITE_API_BASE=/api. In development, proxy /api to Django to avoid CORS and allow cookies:
  - Example (vite.config.ts):
    // export default defineConfig({
    //   server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true, secure: false } } }
    // })
- Token storage
  - Store access in TanStack Store (authStore). On app start, call refresh to hydrate access from refresh cookie
  - Always pass credentials: 'include' so the refresh cookie is sent
- Refresh strategy
  - On 401, attempt a single refresh and retry the original request once; if still unauthorized, redirect to /login with ?redirect=back
  - Optionally preemptively refresh by decoding JWT exp and refreshing shortly before expiry
- Query config
  - Set retry: false for auth-related queries/mutations to avoid retry loops on 401
  - Include authStore.state.accessToken in queryKeys or subscribe to authStore and invalidate ['auth'] on changes
- Environment and paths
  - Define VITE_API_BASE. Ensure endpoint paths match Django (trailing slashes)
  - Be consistent with trailing slashes to avoid 301/308 redirects


- src/routes/(auth)/login.tsx
- src/routes/(auth)/signup.tsx
- src/routes/_layout.tsx (optional shared layout)
- src/routes/_protected.tsx (gate for authenticated pages)

TanStack Router patterns:
- Use createFileRoute file-based API or createRootRoute/createRoute if not using file routing.
- Route guards: use beforeLoad on protected routes to redirect unauthenticated users.

## Query keys and mutations

- Query Keys
  - ['auth','me'] -> current user (queried with Bearer access)

- Mutations
  - login: POST /api/auth/login
  - signup: POST /api/auth/signup
  - refresh: POST /api/auth/token/refresh (no body; uses cookie)

On success of login/signup, store access token in memory (e.g., a TanStack store or React state), set an Authorization header for subsequent requests, invalidate ['auth','me'], and navigate to the intended destination.

## Fetch util (JWT access + refresh cookie)

Example src/lib/auth-client.ts (access in TanStack Store):

```ts
import { Store } from '@tanstack/store'

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

// Global auth store
export const authStore = new Store({
  accessToken: null as string | null,
})

export function setAccessToken(token: string | null) {
  authStore.setState((s) => ({ ...s, accessToken: token }))
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = authStore.state.accessToken
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init, headers })
  if (res.status === 401 && !path.startsWith('/auth/token/refresh')) {
    // Try refresh once
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return request<T>(path, init)
    }
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw Object.assign(new Error(data.detail || data.message || res.statusText), { status: res.status, data })
  }
  return res.json()
}

export async function refreshAccessToken(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/token/refresh/`, { method: 'POST', credentials: 'include' })
  if (!res.ok) return false
  const data = await res.json().catch(() => null)
  if (data?.access) {
    setAccessToken(data.access)
    return true
  }
  return false
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: any) => request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: any) => request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
}
```


## React Query auth hooks


Note: This project uses JWT access tokens, not CSRF/session. Always send Authorization: Bearer <access> once you have it, and include credentials:'include' so the refresh cookie is available for refresh.

```ts
// src/hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, authStore, refreshAccessToken, setAccessToken } from '@/lib/auth-client'

export function useMe() {
  return useQuery({
    queryKey: ['auth','me', authStore.state.accessToken],
    queryFn: async () => {
      await refreshAccessToken() // try hydrate access from cookie
      const data = await api.get<{ user: any }>('/users/me/')
      return data.user
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { username: string; password: string }) =>
      api.post<{ user: any; tokens: { access: string } }>('/auth/login/', body),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access)
      qc.invalidateQueries({ queryKey: ['auth','me'] })
    },
  })

## UI and forms

- Inputs and validation
  - Login: username + password (zod schema)
  - Signup: username, email, password, password_confirm (client-side confirm check)
  - Display DRF field errors mapped to specific fields; display non_field_errors/detail at form level
- Components and layout
  - Use shadcn components: Button, Input, Label (existing)
  - Add a simple Card-style container for centering forms: max-w-sm mx-auto p-6 space-y-4
  - Accessible labels, aria-describedby for errors, and proper autocomplete attributes
- UX behavior
  - Disable submit while pending or if form invalid
  - Show inline validation on blur/change; show server errors after submit
  - After login, navigate to ?redirect= or home; after signup, consider auto-login (backend already returns tokens)
- Email verification
  - If user.email_verified is false, show a banner with "Resend verification" calling /api/users/verify-email/resend/
- Password reset
  - Add "Forgot password?" link to request page (uses password/reset/request and password/reset/confirm flows)

}

export function useSignup() {
  const qc = useQueryClient()

// Optional: subscribe React Query to store changes
// Example: authStore.subscribe(() => qc.invalidateQueries({ queryKey: ['auth'] }))

  return useMutation({
    mutationFn: (body: { username: string; email: string; password: string }) =>
      api.post<{ user: any; tokens: { access: string } }>('/auth/signup/', body),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access)
      qc.invalidateQueries({ queryKey: ['auth','me'] })
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      setAccessToken(null)
      return true
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}
```

## Forms with TanStack React Form + Zod

```ts
// src/routes/(auth)/login.tsx
import { z } from 'zod'
import { useLogin } from '@/hooks/useAuth'
import { useForm } from '@tanstack/react-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@radix-ui/react-label'
import { useNavigate, useSearch } from '@tanstack/react-router'

const schema = z.object({
  username: z.string().min(1),
  password: z.string().min(8),
})

type Values = z.infer<typeof schema>

export default function LoginPage() {
  const login = useLogin()
  const navigate = useNavigate()
  const search = useSearch({ from: '/login' }) as { redirect?: string }

  const form = useForm<Values>({
    defaultValues: { username: '', password: '' },
    onSubmit: async ({ value }) => {
      await login.mutateAsync(value)
      navigate({ to: search?.redirect || '/' })
    },
    validators: {
      onChange: ({ value }) => schema.safeParse(value),
    },
  })

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-2xl font-semibold">Login</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          form.handleSubmit()
        }}
        className="space-y-4"
      >
        <form.Field name="username">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Username</Label>
              <Input
                id={field.name}
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                autoComplete="username"
                required
              />
              {field.state.meta.errors?.[0] && (
                <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>
              )}
            </div>
          )}
        </form.Field>

        <form.Field name="password">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Password</Label>
              <Input
                id={field.name}
                type="password"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                autoComplete="current-password"
                required
              />
              {field.state.meta.errors?.[0] && (
                <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>
              )}
            </div>
          )}
        </form.Field>

        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </Button>

        {login.error && (
          <p className="text-sm text-red-600">{(login.error as any)?.message ?? 'Login failed'}</p>
        )}
      </form>
    </div>
  )
}
```

```ts
// src/routes/(auth)/signup.tsx
import { z } from 'zod'
import { useSignup } from '@/hooks/useAuth'
import { useForm } from '@tanstack/react-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@radix-ui/react-label'
import { useNavigate } from '@tanstack/react-router'

const schema = z.object({
  username: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
  password_confirm: z.string().min(8),
}).refine((v) => v.password === v.password_confirm, { path: ['password_confirm'], message: 'Passwords do not match' })

type Values = z.infer<typeof schema>

export default function SignupPage() {
  const signup = useSignup()
  const navigate = useNavigate()

  const form = useForm<Values>({
    defaultValues: { username: '', email: '', password: '', password_confirm: '' },
    onSubmit: async ({ value }) => {
      const { password_confirm, ...payload } = value
      await signup.mutateAsync(payload)
      navigate({ to: '/' })
    },
    validators: { onChange: ({ value }) => schema.safeParse(value) },
  })

  return (
    <div className="mx-auto max-w-sm p-6">
      <h1 className="mb-4 text-2xl font-semibold">Create your account</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          form.handleSubmit()
        }}
        className="space-y-4"
      >
        <form.Field name="username">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Username</Label>
              <Input id={field.name} value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} required />
              {field.state.meta.errors?.[0] && <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>}
            </div>
          )}
        </form.Field>
        <form.Field name="email">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Email</Label>
              <Input id={field.name} type="email" value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} required />
              {field.state.meta.errors?.[0] && <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>}
            </div>
          )}
        </form.Field>
        <form.Field name="password">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Password</Label>
              <Input id={field.name} type="password" value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} required />
              {field.state.meta.errors?.[0] && <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>}
            </div>
          )}
        </form.Field>
        <form.Field name="password_confirm">
          {(field) => (
            <div className="space-y-2">
              <Label htmlFor={field.name}>Confirm password</Label>
              <Input id={field.name} type="password" value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} required />
              {field.state.meta.errors?.[0] && <p className="text-sm text-red-600">{field.state.meta.errors[0]}</p>}
            </div>
          )}
        </form.Field>
        <Button type="submit" className="w-full" disabled={signup.isPending}>{signup.isPending ? 'Creating…' : 'Create account'}</Button>
        {signup.error && <p className="text-sm text-red-600">{(signup.error as any)?.message ?? 'Signup failed'}</p>}
      </form>
    </div>
  )
}
```

## Router guards (protected routes)

```ts
// src/routes/_protected.tsx
import { useMe } from '@/hooks/useAuth'
import { Outlet, useNavigate, useRouter } from '@tanstack/react-router'
import { useEffect } from 'react'

export default function ProtectedLayout() {
  const { data: user, isLoading } = useMe()
  const navigate = useNavigate()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !user) {
      const to = router.state.location.state?.to ?? router.state.location.href
      navigate({ to: '/login', search: { redirect: to } })
    }
  }, [isLoading, user, navigate, router.state.location])

  if (isLoading) return <div className="p-6">Loading…</div>
  if (!user) return null
  return <Outlet />
}
```

Additionally, a refresh-on-401 is handled by the fetch layer. For route-level guards using file-based routing, use beforeLoad to read the cache and redirect.

## UI with shadcn/ui + Tailwind

- Components to use:
  - Button, Input, Label, Separator, FormMessage (or simple p tags)
  - Card wrapper for centering the form
- Tailwind utility examples
  - Container: mx-auto max-w-sm p-6
  - Titles: text-2xl font-semibold
  - Spacing: space-y-4 / space-y-2
  - Error text: text-sm text-red-600

## Edge cases and behaviors

- Persisting session
  - Access token lives in memory; refresh cookie allows re-hydrating access on page load via refresh endpoint
- Redirect after login
  - Preserve intended path via search param redirect or router state
- Error messaging
  - Show server-side error detail if available (e.g., 400 invalid credentials)
- Rate limiting / lockout
  - Surface generic message after repeated failures
- Email verification
  - Provide a banner if user.email_verified is false; expose actions to resend verification
- Token expiry
  - The fetch layer attempts a one-time refresh on 401; if still unauthorized, route to /login with redirect back

## Implementation checklist

1. Create fetcher with credentials+CSRF
2. Wire QueryClient in main
3. Implement useMe/useLogin/useSignup/useLogout hooks
4. Build login and signup pages using TanStack React Form + shadcn/ui
5. Add routes to the router; mount ProtectedLayout where needed
6. Test happy-path and failure states against Django API

## Example route definitions (TanStack Router v1)

```ts
// src/routes/index.tsx
import { createRootRoute, createRoute, Outlet } from '@tanstack/react-router'
import ProtectedLayout from './_protected'
import LoginPage from './(auth)/login'
import SignupPage from './(auth)/signup'

const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

const signupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/signup',
  component: SignupPage,
})

const protectedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  component: ProtectedLayout,
})

// ...add your private child routes under protectedRoute

export const routeTree = rootRoute.addChildren([
  loginRoute,
  signupRoute,
  protectedRoute,
])
```

## Styling notes (Tailwind v4)

- Prefer utility classes; keep components small and composable
- Respect prefers-reduced-motion; avoid auto-focus jumps
- Inputs must have accessible labels and describe errors with aria-describedby

## Testing

- Unit: field-level validation with zod
- Integration: mock fetch for success/401; ensure redirect logic works
- E2E: attempt login with wrong creds, then with correct creds

## Future extensions

- Password reset flow (request + confirm)
- Social sign-in (Django allauth) – add provider buttons
- Remember me toggle (session age)
- 2FA support
