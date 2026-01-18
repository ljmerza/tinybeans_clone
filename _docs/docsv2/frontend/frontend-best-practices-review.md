# Frontend Best-Practices Review

## Scope & Method
- Stack assessed: React 19, TanStack Router/Query/Form, Tailwind CSS 4, shadcn UI kit, i18next, Vite 7, Vitest 3.
- Focus: gaps between current implementation and recommended practices published by the library authors (TanStack docs, React 19 working group notes, Tailwind 4 migration guide, Testing Library guidelines).
- Process: file-by-file walkthrough of routing, data fetching, form, internationalization, styling, test tooling, and build configuration under `web/`.

## Confirmed Strengths
- Query client factory centralizes sane defaults for caching and retries (`web/src/lib/query/queryClient.ts:33`).
- Router tree is generated once and wrapped in a global error boundary with devtools in development (`web/src/components/AppProviders.tsx:29`, `web/src/routes/__root.tsx:4`).
- TanStack Form usage cleanly composes Zod validators and shared field components (`web/src/features/auth/components/LoginCard.tsx:58`).
- Theme provider guards browser-only APIs and syncs dark-mode class toggling with localStorage (`web/src/features/theme/ThemeProvider.tsx:38`).
- Translation keys are colocated with features and consumed through `useTranslation`, lowering copy drift (`web/src/features/profile/components/ProfileGeneralSettingsCard.tsx:27`).

## Improvement Opportunities

### TanStack Query & Mutation Patterns
- **Add explicit `mutationKey`s and shared metadata**: Custom mutations (login, signup, resend verification, 2FA actions, profile updates) omit `mutationKey`, which reduces deduplication, devtools filtering, and the ability to attach global `mutationCache` handlers (`web/src/features/auth/hooks/authHooks.ts:73`, `web/src/features/auth/hooks/emailVerificationHooks.ts:11`, `web/src/features/twofa/hooks/index.ts:70`). Define factories alongside `queryKeys` (e.g., `authKeys.mutations.login()`) and pass them into `useMutation`.
- **Centralize mutation feedback**: Several mutations still log to the console on failure instead of surfacing localized toasts (`web/src/features/auth/hooks/emailVerificationHooks.ts:19`, `web/src/components/LanguageSwitcher.tsx:34`). Hook a `MutationCache` into `createQueryClient` that routes `meta.toast` metadata through `useApiMessages`, keeping components declarative.
- **Invalidate the auth session after profile changes**: `useUpdateUserProfileMutation` only invalidates the profile query, leaving the session cache stale and preventing language/theme preferences from rehydrating quickly (`web/src/features/profile/hooks/useUpdateUserProfileMutation.ts:34`). Either invalidate `authKeys.session()` or optimistically `setQueryData`.

### Router & Data-Loading Integration
- **Prefer route loaders for protected views**: Only the 2FA routes currently use `queryClient.ensureQueryData` inside loaders (`web/src/routes/profile/2fa/index.tsx:45`). Profile settings, circles dashboards, and invitation flows still fetch within components via `useQuery`. Moving the first fetch into loaders unlocks router-level `pendingComponent` fallbacks and intent-based preloading—key TanStack Router best practices.
- **Adopt lazy route modules for infrequently hit pages**: Heavy feature bundles (2FA setup, invitation flows) are compiled into the main chunk. Replace `createFileRoute` with `createLazyFileRoute` for these paths to leverage React 19 streaming and reduce initial load.
- **Wire route-level pending/error UI**: Components currently render bespoke loading states (`Layout.Loading`, `LoadingState`) inside the view. Exposing the same UI via `Route.pendingComponent`/`Route.errorComponent` keeps behavior consistent with TanStack Router guidance.

### Internationalization Experience
- **Respect persisted language preferences**: i18next always boots in English (`web/src/i18n/config.ts:15`) even when the user profile exposes a saved language. Sync `AuthSessionProvider` with `i18n.changeLanguage(session.user.language)` once the session query resolves (`web/src/features/auth/context/AuthSessionProvider.tsx:34`).
- **Handle language-switch failures gracefully**: The switcher optimistically flips the UI language and then mutates the profile (`web/src/components/LanguageSwitcher.tsx:25`). When the mutation fails, the UI stays in the new language with no feedback. Capture the error, revert `i18n.language`, and present a toast.
- **Exploit dynamic import of locale files**: Both locales are bundled upfront (`web/src/i18n/config.ts:9`). Moving to async namespace loading (via `i18next-http-backend` or Vite dynamic imports) keeps bundles lighter and aligns with i18next best practices for scale.

### Styling & Design System Consistency
- **Map CSS variables into Tailwind tokens**: Custom properties live in `styles.css`, but Tailwind classes still reference hard-coded colors (`web/src/styles.css:19`). Expose these tokens through a Tailwind preset or `theme.extend.colors` so shadcn components and utility classes reference the same palette.
- **Document component API expectations**: shadcn-derived primitives are exported wholesale (`web/src/components/index.ts:19`) without usage guidance. Sharing a MDX or Storybook-lite catalog (config already scaffolded in `components.json`) will help keep component props aligned with shadcn updates.

### Testing & Tooling
- **Register Testing Library matchers once**: Tests use `toBeInTheDocument` but the Vitest config lacks a setup file (`web/vite.config.ts:28`). Add `test: { setupFiles: "src/test-utils/setup-tests.ts" }` that imports `@testing-library/jest-dom/vitest`.
- **Integrate MSW server lifecycle**: `src/test-utils/msw/handlers.ts` is a placeholder, yet no `setupServer` orchestration exists. Wiring MSW into the test setup ensures fetch-heavy hooks (Auth, Circles, 2FA) are covered without manual mocks.
- **Establish realistic integration tests**: Route views (e.g., invitations) rely on manual mocks. Use TanStack Router's `router.update` and `queryClient.setQueryData` helpers in tests to exercise loaders and navigation flows end-to-end.

### Observability & Runtime Quality
- **Publish core web vitals**: `reportWebVitals()` is invoked without a callback (`web/src/main.tsx:33`), so metrics are silently discarded. Pipe them into analytics (Segment, PostHog, etc.) or at least log to the console in development to validate performance.
- **Capture boundary failures**: The ErrorBoundary only reloads the page (`web/src/components/ErrorBoundary.tsx:35`). Best practice is to forward errors to monitoring (Sentry/Bugsnag) before resetting state.

## Suggested Next Steps
1. **Quick wins**: introduce a Vitest setup file, hook MSW to existing tests, and add `mutationKey`s plus toast metadata to the highest-traffic mutations (login/signup, profile update).
2. **Routing uplift**: convert profile and circles routes to loader-based data fetching, exposing shared pending/error components for consistent UX.
3. **i18n polish**: sync language preference from the session, add failure recovery in the switcher, and stage dynamic locale imports to measure bundle savings.
4. **Design system alignment**: expose Tailwind tokens for palette/resizing and draft a lightweight component gallery so future contributions stay within the design guardrails.
