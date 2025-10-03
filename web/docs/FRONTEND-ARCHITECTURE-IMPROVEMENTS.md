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

### 1. App Shell & Bootstrap Flow
- **Observations**: `src/main.tsx` sequences `ensureCsrfToken` and `refreshAccessToken` before rendering and wires providers inline (`src/main.tsx:17-58`). That makes boot flows hard to test, and any new provider or prefetch will further entangle the file.
- **Suggested improvements**:
  - Introduce an `AppProviders` component that encapsulates React Query, Router, Toaster, and any future contexts. Render that from `src/main.tsx`, keeping the entry point declarative.
  - Wrap boot logic in a Suspense-friendly `AppBootstrap` component that performs CSRF + session hydration with React Query or `useEffect`/`startTransition`. That enables showing a branded loading state and gracefully handling errors on startup.
  - Gate `TanStackRouterDevtools` behind an environment flag so it only renders in development builds.
  - Consider loading the precomputed route tree asynchronously to enable code-splitting or future SSR hydration.

### 2. Routing, Guards & Layout Composition
- **Observations**: Auth gating is implemented with `ProtectedRoute` and `PublicOnlyRoute` components that render `<Navigate>` imperatively (`src/components/ProtectedRoute.tsx`, `src/components/PublicOnlyRoute.tsx`). Layout logic determines auth header state directly from the store (`src/components/Layout.tsx:43-66`). The root route wraps the entire tree in a blanket error boundary (`src/routes/__root.tsx`).
- **Suggested improvements**:
  - Use TanStack Router's `beforeLoad`, `loader`, and `context` APIs to declare auth requirements at the route level. This keeps redirects consistent, enables granular pending states, and reduces rerenders compared to `Navigate` components.
  - Define route segments such as `routes/(auth)/` for login/signup, `routes/(protected)/` for pages that require auth, and share layouts via TanStack Router's nested routes. This will better align UI structure with domain boundaries and avoid duplicating layout logic per page.
  - Move header/navigation state into a layout route that consumes a typed `AuthSession` context instead of reading the store in multiple components.
  - Expose a central `NotFound`/`Error` route and let features throw `RouteError`, allowing TanStack Router error boundaries to surface consistent UI.

### 3. Data Layer & API Integration
- **Observations**: `src/features/auth/api/authClient.ts` handles CSRF, token refresh, toasts, and raw fetch calls for auth endpoints (`src/features/auth/api/authClient.ts:21-168`). Other features will need similar behavior but there is no shared abstraction yet. Debug logging leaks to production (`console.log`/`console.warn`).
- **Suggested improvements**:
  - Extract a shared `httpClient` module under `src/lib` that encapsulates fetch defaults, auth headers, CSRF, and error normalization. Have feature-specific clients compose that base to keep domain rules colocated.
  - Use Zod (already in the stack) to validate both request payloads and responses, returning typed data. Pipe those schemas into `@tanstack/react-query` to ensure caches store validated shapes.
  - Standardize query keys (`['auth', 'me']`, `['twofa', 'settings']`, etc.) inside feature modules and export helper builders to prevent string drift across the app.
  - Emit structured errors via a central error class instead of throwing raw `Error` objects; this allows route loaders and hooks to discriminate between auth failures, validation errors, or network issues.
  - Remove console logging in production paths; surface insights through toasts, devtools, or an optional logging sink.

### 4. State Management & Session Boundaries
- **Observations**: The in-memory `authStore` underpins multiple React Query hooks and layout decisions (`src/features/auth/store/authStore.ts`). Query keys in `useMe` depend on `authStore.state.accessToken`, which is read eagerly and can miss updates that occur after mount (`src/features/auth/hooks/index.ts:19-34`). Access tokens never persist across reloads, which may be desired, but there is no differentiation between "unknown" versus "unauthenticated" states.
- **Suggested improvements**:
  - Wrap the TanStack store with a React context (`AuthSessionProvider`) that exposes a stable hook returning `{ status: 'unknown' | 'guest' | 'authenticated', accessToken }`. Route loaders and layouts can react to state transitions without polling the store directly.
  - Emit auth state changes via TanStack Query's `invalidateQueries` or `setQueryData` to guarantee dependent queries update immediately.
  - If session persistence becomes necessary, isolate it behind the provider so storage decisions (sessionStorage vs. memory) remain replaceable.
  - Differentiate initial hydration from explicit logout to avoid flashes of protected content.

### 5. Feature & Shared Module Boundaries
- **Observations**: `src/components` mixes generic primitives and domain-specific elements like `ProtectedRoute`, `AuthCard`, and header actions, which couple shared components to auth state. Feature folders currently export everything from a single `index.ts`, making dependency tracing harder.
- **Suggested improvements**:
  - Adopt a clear feature-slice convention (`entities`, `features`, `widgets`, `pages`, `shared`) or a lighter "app/features/shared" separation. Domain-aware components (AuthCard, guard wrappers, status messages tied to auth) should live under `src/features/auth` or a dedicated `widgets` layer.
  - Limit `index.ts` barrels to feature-level entry points and avoid re-exporting deep submodules indiscriminately. This keeps `import` graphs honest and reduces accidental tight coupling.
  - Consider co-locating route components with their features (e.g., `src/features/auth/routes/login.tsx`) and letting file-based routing import from there. This removes duplication between `routes/` and `features/` for simple wrappers.

### 6. Forms, UI Consistency & Theming
- **Observations**: Each form re-implements field validation wrappers (`src/features/auth/components/LoginCard.tsx:87-142`). Tailwind utility classes are scattered, and some design tokens live in raw CSS (`src/styles.css:1-155`).
- **Suggested improvements**:
  - Create shared form primitives (`Form`, `FormField`, `FormMessage`) that encapsulate TanStack React Form patterns and validation display. Use them across auth and future flows to reduce boilerplate.
  - Centralize design tokens using Tailwind's `@theme` DSL and expose them through a small `theme.ts` helper so components can reference semantic tokens instead of raw utility stacks.
  - Introduce story-driven development (Storybook or Ladle) for complex components (AuthCard, 2FA widgets) to lock down visual contracts and reduce reliance on snapshots.

### 7. Testing, Tooling & Observability
- **Observations**: There are currently no unit or integration tests under `src` (no `*.test.*` files found). Critical flows like login, 2FA setup, and magic link rely solely on manual QA. The toast client and CSRF bootstrap do not have instrumentation.
- **Suggested improvements**:
  - Stand up Vitest-based tests for the auth hooks (`useLogin`, `useMe`) using MSW to simulate API responses. Prioritize coverage for token refresh edge cases and 401 retry logic.
  - Add component tests for forms with Testing Library to verify validation messages and disabled states.
  - Instrument bootstrap (`ensureCsrfToken`, refresh) with optional analytics/logging hooks to help diagnose production failures without resorting to console logs.
  - Automate linting + typechecking + tests in CI; integrate `biome` formatting into pre-commit workflows to keep code style consistent.

## Next Steps
- Prioritize the App Shell and routing guard changes, as they unlock smoother navigation and give other improvements a stable foundation.
- Define a shared HTTP client contract and migrate auth to it first, using that migration as a template for other features.
- Schedule a follow-up iteration to reorganize feature folders and introduce shared form primitives once the base infrastructure is in place.
- Begin assembling a lightweight test suite covering auth flows to prevent regressions as the architecture evolves.
