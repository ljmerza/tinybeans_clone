# React Query Frontend Standardization Plan

## Context
Our React client currently mixes raw `fetch`, bespoke Axios helpers, Redux thunks, and TanStack React Query hooks. This inconsistency makes it difficult to share caching behavior, align typing, and deliver predictable loading/error UX. We already ship `@tanstack/react-query` and route-level providers, but usage is limited to a few recent features.

## Goals
- Establish React Query as the single abstraction for data fetching and mutations.
- Provide consistent query key conventions, error handling, and loading states.
- Improve cache utilization, optimistic UI support, and retry/refresh behavior.
- Simplify testing by sharing mock utilities and deterministic cache priming.

## Non-goals
- Replacing backend endpoints or transport (REST vs GraphQL).
- Rewriting unrelated UI that does not perform network calls.
- Dismantling existing state stores that are unrelated to server data (e.g., UI toggles).

## Success Metrics
- 100% of API interactions (queries + mutations) implemented via React Query hooks.
- Shared query key factory adopted across all feature domains.
- Library test helpers covering network interactions in `web/src/test-utils/`.
- Documentation updated and referenced in onboarding materials.

## Current State Snapshot
- Dependencies already include `@tanstack/react-query` (see `web/package.json`).
- App bootstraps a `QueryClientProvider` in `web/src/components/AppProviders.tsx`.
- Only a handful of feature hooks (`profile`, `auth`, `twofa`, `circles`) rely on React Query.
- Older modules call `fetch` directly or use ad hoc Axios instances without shared caching.
- Tests rely on custom mocks; limited use of `QueryClientProvider` in component specs.

## Guiding Principles
1. **React Query only:** All network interactions must funnel through `useQuery`, `useMutation`, or thin wrappers around them—no raw `fetch`, ad hoc Axios calls, or Redux thunks in UI code.
2. **Feature-first adoption:** Convert within vertical slices (auth, messaging, keeps) to minimize churn.
3. **Preserve UI behavior:** Maintain existing view logic, loading states, and messaging; React Query should replace data plumbing without altering UX unless explicitly scoped.
4. **Typed APIs:** Surface `ApiResponse` types and leverage generics on `useQuery`/`useMutation`.
5. **Declarative cache:** Define query key factories alongside services, not inside components.
6. **Progressive rollout:** Deprecate legacy helpers gradually, keeping shims only as transition aids.
7. **DX friendly:** Provide generated hooks or wrappers where repetitive config is unavoidable.

## Implementation Plan

### Phase 1: Discovery & Catalog
- Inventory all network calls using `rg -g "*.ts*" "fetch("`, Axios instances, Redux thunks, and sagas.
- Classify endpoints by domain, response shape, and side effects.
- Document gaps in typing, error normalization, and retry strategy.

### Phase 2: Foundation
- Define shared modules:
  - `web/src/lib/api/client.ts`: base Axios instance with interceptors, auth headers, and response typing.
  - `web/src/lib/query/queryClient.ts`: centralized `QueryClient` configuration (retry, cache times).
  - `web/src/lib/query/queryKeys.ts`: helper factories (`createUserKeys()`, etc.).
- Publish error/loader handling guidelines: toast strategy, global error boundary triggers.
- Expose test scaffolding: `renderWithQueryClient` helper plus MSW handlers for API mocks.

### Phase 3: Hook Conventions
- Author template for data hooks in each feature:
  ```ts
  export function useFoosQuery(params: FooParams, options?: UseQueryOptions<FooData>) {
    return useQuery({
      ...options,
      queryKey: fooKeys.list(params),
      queryFn: () => foosApi.list(params),
      select: normalizeFooData,
    });
  }
  ```
- Provide matching mutation pattern with optimistic update guidance and cache invalidation helpers.
- Introduce lint rule (custom eslint plugin or shared utility) flagging raw fetch/axios usage outside of `api/` services.

### Phase 4: Migration by Domain
- Prioritize high-impact areas (auth session, messaging threads, keeps timeline, profile data).
- For each domain:
  1. Convert read operations to queries.
  2. Replace mutations with `useMutation`, adding optimistic cache updates where applicable.
  3. Remove redundant local loading/error state; rely on React Query returns.
  4. Update stories/tests to wrap components with `QueryClientProvider`.
- Track progress via checklist in this doc or issue tracker, ensuring zero legacy callers remain.

### Phase 5: QA & Observability
- Run regression tests (`npm run lint`, `npm run test`, targeted E2E suites).
- Monitor network console and React Query Devtools to validate cache hits/misses.
- Instrument key hooks with logging/metrics if needed (e.g., Sentry breadcrumb on query errors).

### Phase 6: Documentation & Rollout
- Update `docs/` with:
  - Query key naming conventions.
  - Sample hook implementations.
  - Testing patterns and MSW expectations.
- Announce changes in engineering sync / Slack, and add to onboarding checklist.
- Archive/deprecate legacy helpers; add codemod or lint autofix where feasible.

## Dependencies & Risks
- **Backend contract stability:** Schema changes affect cache keys and invalidations.
- **Auth token handling:** Ensure interceptors refresh tokens before adopting across app.
- **Bundle size:** React Query is already present, but additional helpers should remain tree-shakeable.
- **Change fatigue:** Stagger migrations to avoid blocking other feature work; coordinate with feature leads.

## Deliverables
- React Query foundation modules (client, keys, test utilities).
- Converted hooks per domain with updated tests.
- Lint guardrail preventing reintroduction of legacy patterns.
- Updated documentation and migration guidance.
- Tracking spreadsheet or GitHub project capturing conversion status.

## Timeline (Tentative)
1. **Week 1:** Discovery + foundational utilities.
2. **Weeks 2–4:** Domain migrations (auth/profile first, then messaging, keeps, miscellaneous).
3. **Week 5:** QA hardening, documentation updates, enforce lint rules.

Adjust timeline based on team capacity; prioritize critical domains if release pressure arises.

## Detailed Architecture

### Data Flow Layers
1. **Transport (fetch only via helpers):** A thin wrapper around `fetch` lives in `web/src/lib/api/client.ts`. It handles base URL, credentials, CSRF, auth headers, and converts responses into `ApiResponse`-shaped objects. No component or feature hook calls `fetch` directly.
2. **Domain services:** Each feature exposes functions such as `usersApi.getProfile()` from `web/src/features/users/api/services.ts`. The functions return typed promises and contain no React-specific logic.
3. **React Query hooks:** All hooks sit in `web/src/features/<domain>/hooks/`. They compose `useQuery`/`useMutation`, reference query key factories, and call the domain services. Components consume only these hooks.
4. **UI components:** Render logic reads `data`, `isLoading`, and `error` from hooks. Any existing local loading/error state is removed in favor of React Query state.

### Shared Modules
- **Query Client:** `web/src/lib/query/queryClient.ts` exports a singleton factory configuring retries, stale times, and error logging. `AppProviders` imports this file, ensuring consistent defaults for tests and devtools.
- **Query Keys:** `web/src/lib/query/queryKeys.ts` provides utility factories (e.g., `createDomainKey("users")`) so each feature can generate keys like `usersKeys.profile(userId)`.
- **HTTP Client:** Migrates existing logic from `httpClient.ts` into `lib/api/client.ts` while keeping helpers for CSRF and auth token retrial. Only this client is allowed to touch `fetch`.
- **Test Utilities:** `web/src/test-utils/` holds `renderWithQueryClient`, a test-friendly `QueryClientProvider`, and MSW handlers kept in `web/src/test-utils/msw/handlers.ts`.

### Hook Templates
```ts
import { usersApi } from "../api/services";
import { usersKeys } from "../api/queryKeys";
import { useQuery, useMutation } from "@tanstack/react-query";

export function useUserProfileQuery(userId: string) {
	return useQuery({
		queryKey: usersKeys.profile(userId),
		queryFn: () => usersApi.getProfile(userId),
		select: (response) => response.data,
	});
}

export function useUpdateUserMutation() {
	return useMutation({
		mutationKey: usersKeys.update(),
		mutationFn: usersApi.update,
		onSuccess: (_, variables, queryClient) => {
			queryClient.invalidateQueries(usersKeys.profile(variables.id));
		},
	});
}
```

Every mutation specifies cache invalidations and optional optimistic updates through helper utilities (`setQueryData`, `getQueryDataSelector`) that we surface from `lib/query/cache.ts`.

### Guardrails
- ESLint rule: Extend Biome or integrate a custom lint rule that disallows `fetch` or `axios` imports outside of `web/src/lib/api/`. During migration, a codemod replaces direct usage with service calls.
- TypeScript helpers: `AwaitedApi<T>` simplifies inference so hooks return plain data while still respecting underlying `ApiResponse` metadata.
- Dev tooling: React Query Devtools is enabled in non-production builds. `window.__TANSTACK_QUERY_CLIENT__` references the shared client for debugging.

### Migration Playbook
1. **Inventory:** Record each raw network call in a migration spreadsheet linked from this doc. Include file path, HTTP method, and target API.
2. **Create services:** For each domain, extract a service module returning typed promises.
3. **Introduce hooks:** Wrap services in React Query hooks, ensure query keys follow the shared conventions, and export them from the domain `index.ts`.
4. **Replace usage:** Update components to use the new hooks. Delete obsolete helpers after verifying no references remain (`rg "<helperName>"`).
5. **Testing:** Adjust component tests to consume `renderWithQueryClient`. Add MSW handlers as needed to simulate network responses.

### Domain-by-Domain Rollout

Break the migration into focused slices so each team can work independently while keeping the app stable.

**1. Auth & Session**
- Files: `features/auth/**`, `route-views/auth/**`, `components/AppBootstrap.tsx`.
- Deliverables:
	- Consolidate services in `features/auth/api/services.ts`.
	- Standardize query keys in `features/auth/api/queryKeys.ts`.
	- Replace `refreshToken` helpers with React Query–driven invalidations where possible.
	- Convert session checks, login, logout, and OAuth hooks to use shared services.
- Testing: Ensure login/logout flows and protected routes behave under token refresh scenarios. Add MSW handlers for auth endpoints.

**2. Profile & Users**
- Files: `features/profile/**`, `route-views/profile/**`.
- Deliverables:
	- Move profile fetch/update logic into `features/profile/api/services.ts`.
	- Implement `usersKeys` for profile, preferences, avatar, etc.
	- Provide hooks (`useUserProfileQuery`, `useUpdateProfileMutation`, ...).
- Testing: Snapshot profile components via `renderWithQueryClient`; prime cache with test utilities.

**3. Circles & Social Graph**
- Files: `features/circles/**`, `route-views/circles/**`.
- Deliverables:
	- Consolidate onboarding, circle creation, and membership APIs.
	- Expose `circlesKeys` (list, detail, members).
	- Replace ad hoc state with `useQuery` and `useMutation`.
- Testing: Cover onboarding flow and circle creation success/error states.

**4. Messaging**
- Files: `features/messaging/**`, relevant route views/components.
- Deliverables:
	- Introduce thread/message services with pagination helpers.
	- Add query keys for thread lists, message lists, drafts.
	- Implement optimistic updates for send/delete operations.
- Testing: Use MSW to validate optimistic UI and cache updates.

**5. Keeps & Content Feed**
- Files: `features/keeps/**`, feed route views.
- Deliverables:
	- Migrate timeline fetches, reactions, and comments to React Query.
	- Create cache utilities for infinite queries (`queryClient.setQueryData` helpers).
	- Align loading spinners with React Query state.
- Testing: Ensure infinite scroll works with mocked API (MSW + virtualized lists).

**6. Miscellaneous Integrations**
- Files: `integrations/**`, shared components making network requests.
- Deliverables:
	- Audit for remaining `fetch` usage; port to services + hooks.
	- Provide domain-specific query keys (e.g., third-party integrations).
- Testing: Backfill unit tests once services are standardized.

Sequence tips:
- Finish one domain before starting the next to avoid conflicts.
- Update the migration tracker after each domain to keep visibility.
- Cross-team review major domain PRs to ensure conventions remain consistent.

### Operational Considerations
- **Error messaging:** All errors surface through `useApiMessages()` and domain-specific toasts. To avoid double toasts, hooks accept an optional `onError` but default to shared behavior.
- **Auth flows:** Token refresh remains in `features/auth`, but React Query handles retries by triggering `refreshAccessToken` via interceptors. Hooks that require fresh auth tokens include `networkMode: "always"` when necessary.
- **SSR/Prefetching:** Although not an immediate goal, the shared client exposes `prefetchQuery` helpers for future server rendering or route loaders.
- **Performance:** Use `select` to narrow data, enabling stable reference equality and reducing rerenders. Cache times align with backend TTLs documented in each service file.

### Deliverable Checklist
- [x] `web/src/lib/api/client.ts` and `web/src/lib/query/queryClient.ts` created, adopted by `AppProviders`.
- [x] Query key factories live alongside each feature (`features/<domain>/api/queryKeys.ts`).
- [x] Hooks exported via `features/<domain>/hooks/index.ts` without raw network calls.
- [x] Legacy helpers and direct `fetch` usage removed or annotated with TODO + owner.
- [x] `web/src/test-utils/` ready with Query Client fixtures and MSW handlers.
- [ ] Biome/ESLint rule added to guard against future regressions.
- [x] Documentation (this file + onboarding) updated with final conventions.

> **Guardrail:** `npm run check` now runs `scripts/check-no-raw-fetch.mjs` before `biome check`. The script fails if it finds `fetch(` outside a short allowlist (`src/lib/api/client.ts`, `src/lib/httpClient.ts`, `src/lib/csrf.ts`, `src/features/auth/utils/refreshToken.ts`, `src/features/twofa/api/services.ts`). Add new network calls via feature services so they pass this gate.
