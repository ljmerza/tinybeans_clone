# Frontend Improvement Plan (web)

## Context & Guiding Principles
- Build on the existing React 19 + Vite stack with TanStack Router/Query/Form, Tailwind 4, and shadcn-ui.  
- Prefer incremental refinements over large rewrites; preserve the solid structure already in place (`AppBootstrap`, `AppProviders`, feature folders).  
- Lean on first-party guidance from TanStack (query key factories, router loaders, mutation cache patterns) and Tailwind/shadcn best practices (design tokens, composition).  
- Keep developer operations simple: Biome remains the single source for lint/format, Vitest + Testing Library for UI verification, T3Env for runtime safety.

## Current Strengths
- `AppBootstrap` orchestrates CSRF + session hydration cleanly before rendering (`web/src/components/AppBootstrap.tsx:1`).  
- Route tree generation and router instance are centralized once per module (`web/src/components/AppProviders.tsx:24`).  
- Server interactions are abstracted behind `createHttpClient`, keeping feature API clients thin (`web/src/lib/httpClient.ts:52`).  
- Forms already lean on `@tanstack/react-form` with zod validators (e.g. `web/src/features/auth/components/LoginCard.tsx:48`).  
- Shared UI primitives and feedback components live under `web/src/components`, giving a consistent experience.

## Roadmap Overview
- **Stabilize (next sprint)** – tighten data fetching, cleanup debugging residue, and finish internationalization in user-facing surfaces.  
- **Enhance (1-2 months)** – integrate router loaders with React Query, raise design consistency, and automate feedback/error handling.  
- **Evolve (later)** – uplift performance, theming, and observability once the above foundations are in place.

## Stabilize (Short Term)
- ✅ **Codify TanStack Query keys & selectors**  
  Implemented shared factories (`web/src/features/auth/api/queryKeys.ts`, `web/src/features/twofa/api/queryKeys.ts`) and refactored auth/2FA hooks to use them for cache consistency.
- ✅ **Remove console debugging & surface structured errors**  
  Consolidated 2FA mutation handling in `web/src/features/twofa/hooks/index.ts`, routing feedback through `useApiMessages`, `extractApiError`, and `showToast`.
- ✅ **Complete i18n coverage for feature views**  
  Localized remaining 2FA flows (setup wizards, settings, verification) and expanded locale dictionaries (`web/src/i18n/locales/en.json`, `web/src/i18n/locales/es.json`) with supporting strings.
- ✅ **Document form conventions**  
  Added TanStack Form + Zod guidance to `web/README.md`, covering validation reuse, shared components, and internationalized messaging.

## Enhance (Mid Term)
- ✅ **Router ↔ Query integration using loaders**  
  Added loaders for the 2FA routes so navigation prefetches via the shared QueryClient context (`web/src/routes/profile/2fa/settings.tsx`, `web/src/routes/profile/2fa/setup/index.tsx`, `web/src/routes/profile/2fa/trusted-devices.tsx`).
- ✅ **Shared form primitives & status messaging**  
  Introduced reusable `FormField`/`FormActions` wrappers and a shared `FieldError` renderer to normalize labels, helper text, and API feedback across auth experiences (`web/src/components/form/FormField.tsx:1`, `web/src/components/form/FormActions.tsx:1`, `web/src/components/FieldError.tsx:1`). Updated login, signup, password reset, and magic link flows to use the new primitives (`web/src/features/auth/components/LoginCard.tsx:1`, `web/src/features/auth/components/SignupCard.tsx:1`, `web/src/features/auth/components/PasswordResetRequestCard.tsx:1`, `web/src/features/auth/components/PasswordResetConfirmCard.tsx:1`, `web/src/features/auth/components/MagicLinkRequestCard.tsx:1`).
- **Centralized mutation feedback policy**  
  - Extend `AppProviders` with a custom `MutationCache` that pipes success/error states into `useApiMessages` / `sonner`, reducing per-hook boilerplate (`web/src/components/AppProviders.tsx:33`).  
  - Adopt TanStack Query’s `mutationCache.onError` patterns while preserving feature-level overrides via options.
- **Accessibility checks for dialogs & toasts**  
  - Audit aria attributes and focus management for dialogs, toasts, and new form wrappers to stay aligned with Radix/shadcn accessibility guarantees; document any required follow-up work.
- **Design system alignment**  
  - Map the CSS custom properties in `web/src/styles.css:21` to Tailwind theme tokens and document usage, ensuring shadcn components consume the same palette.  
  - Create a Storybook-lite environment (or a Vite route) showcasing UI atoms for visual regression and team onboarding.
- **Typed API clients with response adapters**  
  - Introduce response mappers alongside `createHttpClient` so features return typed domain objects (e.g. adapt 2FA API payloads before they reach components), following React Query cache best practices.

## Evolve (Long Term)
- **Progressive data loading & streaming**  
  - Explore React 19 `use` with TanStack Router deferred data for large dashboards once backend endpoints demand it.  
  - Adopt skeleton/suspense boundaries per layout region, building on `Layout.Loading` (`web/src/components/Layout.tsx:27`).
- **Theming & brand scaling**  
  - Parameterize `AppProviders` with a theme context that toggles Tailwind CSS custom properties (light/dark, seasonal palettes).  
  - Align shadcn component tokens with marketing guidelines without fragmenting utility classes.
- **Observability & quality gates**  
  - Wire `reportWebVitals` (`web/src/reportWebVitals.ts:1`) into analytics and add lightweight Sentry (or equivalent) integration for caught errors surfaced via `ErrorBoundary` (`web/src/components/ErrorBoundary.tsx:1`).  
  - Incrementally add Vitest + Testing Library suites around critical flows (login, 2FA enablement) to guard against regressions as the app grows.

## Next Steps
1. Share the completed Stabilize work with the team and reprioritize the **Enhance** items based on current roadmap needs.  
2. Track remaining enhancements (router loaders, mutation cache policy, design system alignment) as individual tickets on the frontend tech-debt board.  
3. Plan an i18n QA pass once new features land to keep locale files current, leveraging the expanded translation keys added in this phase.
