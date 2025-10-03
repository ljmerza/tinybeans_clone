# Frontend Architecture Improvements

## Context
The web client is built with Vite, React 19, TanStack Router, TanStack Query, TanStack React Form, Tailwind CSS 4, and a small in-memory store for auth state. The codebase already leans toward a feature-first structure (`src/features`, `src/routes`, `src/components`), but several cross-cutting patterns are ad-hoc (bootstrap logic lives in `src/main.tsx`, routing guards are implemented as components, API access is concentrated in the auth feature, etc.). This document highlights the most impactful architectural upgrades to improve maintainability, resilience, and developer experience.

## Implementation Status

✅ = Implemented | 🚧 = Partially Implemented | ⏳ = Not Yet Implemented

See `IMPLEMENTATION-COMPLETE.md` and `IMPLEMENTATION-SUMMARY.md` for detailed implementation documentation.

## High-Priority Themes
1. ✅ **Move bootstrap & provider composition out of `src/main.tsx`** to a dedicated App shell that can better coordinate async startup, suspense, and error handling.
2. ✅ **Adopt route-level lifecycle hooks instead of component wrappers** so auth and loading flows leverage TanStack Router features and remain declarative.
3. ✅ **Extract a reusable HTTP/data layer** that formalizes API shape, normalizes errors, and integrates deeply with TanStack Query across features beyond auth.

## Recommendations by Area

### 1. ✅ App Shell & Bootstrap Flow (IMPLEMENTED)
- **Status**: ✅ **Fully Implemented**
- **What was implemented**:
  - ✅ Created `AppProviders.tsx` that encapsulates React Query, Router, Toaster, and AuthSession contexts
  - ✅ Created `AppBootstrap.tsx` that handles async CSRF + session hydration with proper loading/error states
  - ✅ Simplified `src/main.tsx` to be declarative (64 → 41 lines)
  - ✅ Added conditional `TanStackRouterDevtools` rendering (only in `import.meta.env.DEV`)
- **Original observations**: `src/main.tsx` sequences `ensureCsrfToken` and `refreshAccessToken` before rendering and wires providers inline (`src/main.tsx:17-58`). That makes boot flows hard to test, and any new provider or prefetch will further entangle the file.
- **Remaining work**: 
  - ⏳ Consider loading the precomputed route tree asynchronously to enable code-splitting or future SSR hydration

### 2. 🚧 Routing, Guards & Layout Composition (PARTIALLY IMPLEMENTED)
- **Status**: 🚧 **Partially Implemented**
- **What was implemented**:
  - ✅ Created route guard utilities (`requireAuth`, `requireGuest`) using TanStack Router's `beforeLoad` hook
  - ✅ Migrated 7 routes to use `beforeLoad` guards instead of component wrappers
  - ✅ Improved layout to use `useAuthSession()` context instead of direct store access
  - ✅ Root route has error boundary in place
- **Original observations**: Auth gating is implemented with `ProtectedRoute` and `PublicOnlyRoute` components that render `<Navigate>` imperatively (`src/components/ProtectedRoute.tsx`, `src/components/PublicOnlyRoute.tsx`). Layout logic determines auth header state directly from the store (`src/components/Layout.tsx:43-66`). The root route wraps the entire tree in a blanket error boundary (`src/routes/__root.tsx`).
- **Remaining work**:
  - ⏳ Define route segments such as `routes/(auth)/` for login/signup, `routes/(protected)/` for pages that require auth
  - ⏳ Share layouts via TanStack Router's nested routes
  - ⏳ Expose a central `NotFound`/`Error` route and let features throw `RouteError`
  - 🚧 Deprecate and eventually remove `ProtectedRoute` and `PublicOnlyRoute` components (currently kept for backward compatibility)

### 3. ✅ Data Layer & API Integration (IMPLEMENTED)
- **Status**: ✅ **Fully Implemented**
- **What was implemented**:
  - ✅ Created `src/lib/httpClient.ts` - shared HTTP client with CSRF, auth headers, and error normalization
  - ✅ Migrated `authClient.ts` to use the shared HTTP client
  - ✅ Removed console.log/console.warn from production paths
  - ✅ Standardized error handling with proper type support
  - ✅ Added configurable success/error toast hooks
- **Original observations**: `src/features/auth/api/authClient.ts` handles CSRF, token refresh, toasts, and raw fetch calls for auth endpoints (`src/features/auth/api/authClient.ts:21-168`). Other features will need similar behavior but there is no shared abstraction yet. Debug logging leaks to production (`console.log`/`console.warn`).
- **Remaining work**:
  - ⏳ Use Zod to validate both request payloads and responses, returning typed data
  - ⏳ Standardize query keys (`['auth', 'me']`, `['twofa', 'settings']`, etc.) and export helper builders
  - ⏳ Emit structured errors via a central error class for better discrimination between auth failures, validation errors, or network issues

### 4. ✅ State Management & Session Boundaries (IMPLEMENTED)
- **Status**: ✅ **Fully Implemented**
- **What was implemented**:
  - ✅ Created `AuthSessionProvider` context that wraps the TanStack store
  - ✅ Exposed stable `useAuthSession()` hook with typed states: `'unknown' | 'guest' | 'authenticated'`
  - ✅ Updated components and routes to use context instead of direct store access
  - ✅ Differentiated initial hydration from explicit logout states
- **Original observations**: The in-memory `authStore` underpins multiple React Query hooks and layout decisions (`src/features/auth/store/authStore.ts`). Query keys in `useMe` depend on `authStore.state.accessToken`, which is read eagerly and can miss updates that occur after mount (`src/features/auth/hooks/index.ts:19-34`). Access tokens never persist across reloads, which may be desired, but there is no differentiation between "unknown" versus "unauthenticated" states.
- **Remaining work**:
  - ⏳ Emit auth state changes via TanStack Query's `invalidateQueries` or `setQueryData` to guarantee dependent queries update immediately
  - ⏳ If session persistence becomes necessary, isolate it behind the provider so storage decisions remain replaceable

### 5. ⏳ Feature & Shared Module Boundaries (NOT YET IMPLEMENTED)
- **Status**: ⏳ **Not Yet Implemented**
- **Original observations**: `src/components` mixes generic primitives and domain-specific elements like `ProtectedRoute`, `AuthCard`, and header actions, which couple shared components to auth state. Feature folders currently export everything from a single `index.ts`, making dependency tracing harder.
- **Suggested improvements**:
  - Adopt a clear feature-slice convention (`entities`, `features`, `widgets`, `pages`, `shared`) or a lighter "app/features/shared" separation. Domain-aware components (AuthCard, guard wrappers, status messages tied to auth) should live under `src/features/auth` or a dedicated `widgets` layer.
  - Limit `index.ts` barrels to feature-level entry points and avoid re-exporting deep submodules indiscriminately. This keeps `import` graphs honest and reduces accidental tight coupling.
  - Consider co-locating route components with their features (e.g., `src/features/auth/routes/login.tsx`) and letting file-based routing import from there. This removes duplication between `routes/` and `features/` for simple wrappers.

### 6. ⏳ Forms, UI Consistency & Theming (NOT YET IMPLEMENTED)
- **Status**: ⏳ **Not Yet Implemented**
- **Original observations**: Each form re-implements field validation wrappers (`src/features/auth/components/LoginCard.tsx:87-142`). Tailwind utility classes are scattered, and some design tokens live in raw CSS (`src/styles.css:1-155`).
- **Suggested improvements**:
  - Create shared form primitives (`Form`, `FormField`, `FormMessage`) that encapsulate TanStack React Form patterns and validation display. Use them across auth and future flows to reduce boilerplate.
  - Centralize design tokens using Tailwind's `@theme` DSL and expose them through a small `theme.ts` helper so components can reference semantic tokens instead of raw utility stacks.
  - Introduce story-driven development (Storybook or Ladle) for complex components (AuthCard, 2FA widgets) to lock down visual contracts and reduce reliance on snapshots.

### 7. ⏳ Testing, Tooling & Observability (NOT YET IMPLEMENTED)
- **Status**: ⏳ **Not Yet Implemented**
- **Original observations**: There are currently no unit or integration tests under `src` (no `*.test.*` files found). Critical flows like login, 2FA setup, and magic link rely solely on manual QA. The toast client and CSRF bootstrap do not have instrumentation.
- **Suggested improvements**:
  - Stand up Vitest-based tests for the auth hooks (`useLogin`, `useMe`) using MSW to simulate API responses. Prioritize coverage for token refresh edge cases and 401 retry logic.
  - Add component tests for forms with Testing Library to verify validation messages and disabled states.
  - Instrument bootstrap (`ensureCsrfToken`, refresh) with optional analytics/logging hooks to help diagnose production failures without resorting to console logs.
  - Automate linting + typechecking + tests in CI; integrate `biome` formatting into pre-commit workflows to keep code style consistent.

## Next Steps

### ✅ Completed (Phase 1)
- ✅ App Shell and provider composition
- ✅ Route-level auth guards implementation
- ✅ Shared HTTP client extraction
- ✅ Auth session context provider
- ✅ Bootstrap flow improvements
- ✅ Production-ready devtools and logging

### 🔄 Recommended Next Priorities (Phase 2)
1. **Route Layout Composition** - Define route segments (`routes/(auth)/`, `routes/(protected)/`) with shared layouts
2. **Query Key Standardization** - Export helper builders for consistent query keys across features
3. **Structured Error Classes** - Create error hierarchy for better error discrimination
4. **Zod Response Validation** - Add schema validation to HTTP client responses

### 📋 Future Enhancements (Phase 3)
- Shared form primitives to reduce boilerplate
- Design token system with Tailwind `@theme` DSL
- Testing infrastructure (Vitest + MSW)
- Feature folder reorganization
- Story-driven development setup
