# Internationalization Audit & Improvement Plan

## Current State Overview

### Backend (Django)
- Global language settings are still English-only. `LANGUAGE_CODE` is pinned to `"en-us"` and the middleware stack omits `django.middleware.locale.LocaleMiddleware`, so Django never activates per-request locales (mysite/mysite/config/settings/base.py:108,199).
- Internationalized strings exist (for example, `gettext_lazy` usages in permission guards) but no `locale/` directories or compiled `.po` files are checked in, so those calls always resolve to English (e.g., `mysite/circles/views/invitations.py` permission checks).
- The user model exposes a `language` field with validated choices (mysite/users/models/user.py:180-185), yet nothing in the request pipeline reads it to set `translation.activate(user.language)` or otherwise influence outbound content.
- REST responses only standardize validation errors; other exception types (403/404/500) fall back to DRF defaults, which means English messages leak through and the frontend cannot translate them (mysite/mysite/exception_handlers.py:61-70).
- There is no automated check that backend `i18n_key` literals have matching entries in the frontend locale bundles.

### Frontend (React)
- The i18next instance loads `en` and `es`, but defaults to `"en"` and never inspects persisted user preference or browser locale (web/src/i18n/config.ts:12-25).
- The root provider tree omits an explicit `<I18nextProvider>` and does not hydrate the language based on the authenticated user profile, so every fresh load starts in English even when the backend has a stored preference (web/src/components/AppProviders.tsx:51-64).
- A `LanguageSwitcher` component exists but is not mounted anywhere in the UI, leaving no way for users to change their language after sign-in (web/src/components/LanguageSwitcher.tsx:19-105).
- Shared UI primitives now support i18n fallbacks, but some call sites still hard-code English strings (e.g., web/src/components/AppBootstrap.tsx:61-99); ensure consuming screens pass translation keys where possible.
- The i18n utilities file re-exports `ApiMessage`/`ApiResponse` without importing them, which currently breaks strict TypeScript builds and blocks consumers from relying on those types (web/src/i18n/notificationUtils.ts:8-34).
- Developer docs reference an `EXAMPLES.tsx` file that is not present, creating dead links for anyone onboarding to the i18n module (web/src/i18n/README.md:132-138).

## Risks & Impact
- **Broken expectations for saved preferences:** Users can set a language via the API, but every session falls back to English; this erodes trust in personalization.
- **Non-translatable error states:** Permission errors and other server-side failures surface as raw English strings, undermining localization efforts and complicating frontend handling.
- **Maintenance drag:** Storing every key in a single monolithic namespace with no tooling checks makes it easy to ship missing or stale translations.
- **Tooling gaps:** Type errors in `notificationUtils` and missing examples slow developers down and discourage extending the i18n system.

## Recommended Improvements

### Immediate (stabilize current functionality)
1. **Hydrate language on bootstrap.** After fetching the current user (or profile), call `i18n.changeLanguage(user.language)` so the UI honors stored preferences. A lightweight hook in `AppBootstrap` or the auth store would close this gap.
2. **Surface the language switcher.** Mount `LanguageSwitcher` (and its compact variant for narrow layouts) in the global header and guard the backend PATCH call when the viewer is unauthenticated.
3. **Localize shared primitives.** Replace hard-coded fallbacks in standard loading/error components and bootstrap flows with translation keys (e.g., `common.loading`, `errors.generic`). Provide sensible defaults via `t(key, { defaultValue })`.
4. **Fix i18n type exports.** Import and re-export `ApiMessage`/`ApiResponse` directly from `@/types` inside `notificationUtils.ts` so downstream code and builds stay healthy.

### Near-Term (next sprint or two)
1. **Apply user language on the server.** Introduce middleware that activates `request.user.language` (when authenticated) or honors `Accept-Language`, and add `LANGUAGES`, `LOCALE_PATHS`, plus compiled message catalogs to the repo.
2. **Normalize API error responses.** Extend `custom_exception_handler` (and any DRF exception hooks) to translate `PermissionDenied`, `NotAuthenticated`, and unforeseen errors into structured `i18n_key` payloads instead of English strings.
3. **Namespace locale bundles.** Break the single `translation` namespace into feature-scoped files (`auth`, `twofa`, `common`, etc.) to simplify maintenance and enable lazy loading later.
4. **Restore developer examples.** Either add the missing `EXAMPLES.tsx` under `web/src/i18n/` or update the README to point at working samples so new contributors see canonical patterns.

### Longer-Term (process & automation)
1. **Translation key linting.** Add a script/CI job that scans backend `i18n_key` literals and verifies they exist in every supported locale JSON. Fail builds when keys drift.
2. **Crowdin/PO pipeline.** Decide on a translation management workflow (e.g., Django `.po` files + Crowdin or another SaaS) to keep backend/admin strings in sync with the frontend catalog.
3. **Automated regression tests.** Cover key flows (auth success/failure, 2FA, profile updates) with Vitest/Jest stories that assert translated copy changes when `i18n.changeLanguage("es")` is invoked.
4. **Runtime key surfacing.** Consider adding an in-app developer overlay (enabled via feature flag) that lists missing translations, easing QA in multilingual releases.

## Open Questions & Follow-Ups
- Do we want backend-rendered emails/notifications to share the same translation sources, or should they use separate `.po` catalogs?
- Should the saved user language trump browser locale everywhere, or only after explicit opt-in?
- Are additional locales planned in the short term? If so, prioritize tooling automation earlier to avoid manual JSON edits.

Document prepared to guide the next iteration on internationalization hygiene; feel free to adapt priority ordering to match sprint bandwidth.
