# Email-Only Identity Transition Plan

## Context

- The current stack exposes `username` throughout authentication, invitations, child upgrades, notifications, and the React client (see e.g. `mysite/users/models/user.py:22-249`, `mysite/auth/views.py:110-647`, `web/src/features/auth/components/LoginCard.tsx:39-165`).
- Product now wants to rely on email as the sole identifier for account creation and login; usernames must be removed from the schema and all dependent logic. The app is still in development, so schema-breaking changes are acceptable without immediate data migrations.

## Goals

1. Make email the only credential required for signup, login, password reset, invitations, and onboarding.
2. Remove the `username` column/field from the custom `User` model and any ORM/query logic, serializers, admin screens, rate limits, and services that currently depend on it.
3. Update every backend endpoint, email template, notification, and serializer to stop emitting `username`.
4. Update the entire frontend (forms, validations, hooks, types, translations, tests) so UX copy and payloads reference email only.
5. Refresh documentation, ADRs, stories, and helper scripts so no contributor guidance references usernames.

## Non-Goals / Out of Scope

- Building a replacement “display name” feature. We can leverage existing `first_name`/`last_name` or default to email for labels, but a richer profile naming system is deferred.
- Migrating production data (no prod traffic yet). Once prod exists, a data backfill would be required.
- Supporting mixed-identifier logins (username or email). The end-state is email-only everywhere.

## Constraints & Assumptions

- Because the app is still under heavy development, we can change the schema directly; migrations will be generated later when needed.
- Third-party auth still relies on Django’s auth backend. After we set `USERNAME_FIELD = 'email'`, we must ensure admin logins and DRF authentication code paths still align.
- Security posture (rate limiting, messaging) must remain equivalent or better after removing username identifiers.

## Current Usage Inventory

### Data Model & Admin

- `mysite/users/models/user.py:22-249` enforces username creation, ordering, and `REQUIRED_FIELDS`; `AbstractUser.__str__` also returns username.
- `mysite/users/admin.py:30-221` lists/searches on username; inherited `DjangoUserAdmin` expects username form fields.
- `mysite/users/serializers/core.py:20-54` and `mysite/users/serializers/profile.py:10-20` include username in API responses.
- `mysite/users/serializers/children.py:24-88` plus `mysite/users/views/children.py:201-206` require usernames when upgrading child accounts.
- `mysite/users/management/commands/seed_demo_data.py:51-201` seeds demo credentials with usernames.
- `mysite/users/tests/**/*.py` (models, serializers, edge cases, onboarding) assert username behaviors that will no longer exist.

### Authentication & Security Flows

- `mysite/auth/serializers.py:16-120` require username for signup/login/password-reset identifiers.
- `mysite/auth/views.py:110-647` responds with usernames, rate-limits on `post:username`, and documents username/password logins.
- `mysite/auth/services/google_oauth_service.py:382-429` generates usernames for new Google accounts; two-factor and trusted-device services (`mysite/auth/services/twofa_service.py:53`, `recovery_code_service.py:26-67`, `trusted_device_service.py:265-271`) log/display usernames.
- `mysite/auth/models.py:141-347` string representations use usernames; admin search fields in `mysite/auth/admin.py:17-67` look up `user__username`.
- Tests under `mysite/auth/tests/` (2FA login, OAuth service, etc.) create and assert usernames.
- `_docs/guides/security/*.md` and ADR-003 reference username-based rate limits and identifiers.

### Domain Features (Circles, Keeps, Child Upgrades)

- Invites: `mysite/circles/serializers/circles.py:127-205`, `mysite/circles/views/invitations.py:75-500`, `mysite/circles/models/invitation.py:74`, and `mysite/circles/tasks.py:39-82` allow username lookup, sort by username, and include usernames in payloads.
- Membership listings: `mysite/circles/views/memberships.py:43` orders by `user__username`; `mysite/circles/models/membership.py:42` indexes on username.
- Keeps & reactions: serializers/admin/tests (`mysite/keeps/serializers/*.py`, `mysite/keeps/admin.py:73-261`, `mysite/keeps/tests/*`) expose `*_username` fields.
- Child upgrade serializers (`mysite/users/serializers/children.py`) and audit logs rely on username uniqueness.

### Emails & Notifications

- `mysite/emails/mailers.py:136-207` populates `username` template variables; HTML templates under `mysite/emails/email_templates/*.email.html` greet users via `{{ username }}`.
- Notification utils and audit logs embed usernames in strings (see `mysite/auth/models.py:141-347`, `mysite/users/tests/test_invitation_roles.py:355` etc.).

### Frontend / React Client

- Auth UX: `web/src/features/auth/components/LoginCard.tsx`, `SignupCard.tsx`, and `PasswordResetRequestCard.tsx` collect/display usernames; validations live in `web/src/lib/validations/schemas/{login,signup,common}.ts`.
- Auth types/hooks: `web/src/features/auth/types/auth.types.ts`, `web/src/features/auth/oauth/types.ts`, and API hook payloads all require `username`.
- Circles UI: `web/src/features/circles/types.ts`, hooks, components, and utilities (e.g., `web/src/features/circles/utils/invitationHelpers.ts`, `route-views/invitations/accept.tsx`) read/write usernames.
- 2FA client contracts (`web/src/features/twofa/types/twofa.types.ts`) expect username in responses.
- Shared types and tests under `web/src/**/__tests__` assert username-specific behavior.
- Translations (`web/src/i18n/locales/{en,es}.json`) and form docs under `_docs/forms/*.md` describe username-based copy.

### Documentation & Guidance

- Architecture docs (`docs/architecture.md`, ADR-003/004, ADR-010) and PRD/stories (`docs/prd.md`, `docs/stories/*.md`, `docs/adrs/0001-circle-invite-flow.md`) promise username/email invite parity and username/password login.
- Security write-ups (`_docs/guides/security/*.md`, `_docs/guides/security/SECURITY_IMPROVEMENTS_IMPLEMENTED.md:100-324`) explain per-username rate limits.
- Onboarding guides (`README.md`, `DEVELOPMENT.md`, `_docs/forms/*.md`) include username instructions that must be rewritten.

## Implementation Workstreams

1. **Schema & ORM**
   - Remove the `username` field by setting `username = None`, `USERNAME_FIELD = 'email'`, and `REQUIRED_FIELDS = []` in `mysite/users/models/user.py`.
   - Rewrite `UserManager` (`mysite/users/models/user.py:22-97`) to accept only email/password, normalizing and enforcing uniqueness.
   - Update `Meta.ordering` to `['email']` (or `['-date_joined']` if preferred) and override `__str__` to return `self.email` or `get_full_name()`.
   - Touch admin classes (`mysite/users/admin.py`, `mysite/auth/admin.py`, `mysite/circles/admin.py`, `mysite/keeps/admin.py`) to search by email/ID instead of username and adjust `fieldsets` so Django admin works without username inputs.
   - Update fixtures/seeds (`mysite/users/management/commands/seed_demo_data.py`), factories, and tests to drop username setup.
   - Ensure any DB indexes (`mysite/users/migrations/0001_initial.py`) referencing username are removed before regenerating migrations later.

2. **Authentication & Security Endpoints**
   - Signup/login serializers (`mysite/auth/serializers.py`) should only request `email` and `password`; adjust copy, validation errors, and tests.
   - Login view (`mysite/auth/views.py:110-200`) must accept `email`, update OpenAPI docs, swap rate-limit keys to use `post:email` (or IP-only), and ensure we still log attempts without leaking whether an email exists.
   - Password reset/email verification flows should take an email field only; update identifier language and responses.
   - Update JWT payloads, 2FA responses, and `success_response` helpers so `user` objects never include username.
   - OAuth service (`mysite/auth/services/google_oauth_service.py:382-429`) needs to stop generating usernames. Ensure new Google-only users are created through `create_user` or equivalent that sets email as the login identifier.
   - Adjust two-factor/recovery/trusted-device services to use email/full name in logs, audit data, and template contexts.
   - Refresh related tests (`mysite/auth/tests/**`) to assert email-only behavior and updated error messaging.

3. **Domain Logic (Circles, Keeps, Child Upgrades)**
   - Invitations: remove username parameters from `CircleInvitationCreateSerializer` and DRF views; ensure dedupe happens on email + `invited_user_id`. Update `CircleInvitation` model string repr (`mysite/circles/models/invitation.py:74`) and any tasks/emails referencing inviter usernames.
   - Membership ordering (`mysite/circles/views/memberships.py:43`, `mysite/circles/models/membership.py:42`) should sort by email or `full_name`.
   - Keeps/comments/reactions must expose meaningful author info (e.g., `created_by_email`, `created_by_name`); adjust serializers and tests.
   - Child upgrade serializers must replace username collection with either `email` only or another optional display field—clarify whether to reuse `display_name` or `first_name`. Update `ChildProfileUpgradeConfirmSerializer` accordingly.
   - Anywhere `UserSerializer`/`PublicUserSerializer` is consumed (circles, invitations, onboarding) must shift to email (plus derived display data if available) so frontend components remain functional.

4. **Emails & Notifications**
   - Replace `username` template variables with `email` or a derived friendly name across `mysite/emails/mailers.py` and `mysite/emails/email_templates/*.html`.
   - Ensure mail contexts still provide fallback values (e.g., `user.get_full_name() or user.email`).
   - Update notification/audit strings in `mysite/auth/models.py` and any Celery tasks so logs stay informative without usernames.

5. **Frontend & UX**
   - Forms: update `LoginCard`, `SignupCard`, and `PasswordResetRequestCard` to collect email, adjust placeholders/auto-complete attributes, and show copy like “Email address”.
   - Validations: remove `usernameSchema` from `web/src/lib/validations/schemas/common.ts`, simplify login/signup schemas to just email/password, and strip identifier helper text referencing usernames.
   - Types/hooks: modify `AuthUser`, `LoginRequest`, `SignupRequest`, circle-related types, and 2FA response types to remove username fields; update API hooks/mutations accordingly.
   - Circles UI: update invitation controllers/utilities to work with email-only identifiers; ensure dedupe logic uses `invited_user.email` or `id`.
   - Translations: rewrite strings in `web/src/i18n/locales/en.json` and `es.json` that mention usernames (“Email or username”, “Username is required”, etc.), and regenerate any docs under `_docs/forms/`.
   - Frontend tests (Vitest/RTL) referencing usernames need new fixtures or expectations.

6. **Docs & Internal Guides**

   - Update PRD, ADRs (`docs/prd.md`, `docs/adrs/0001-circle-invite-flow.md`, `docs/architecture.md`, ADR-003/004/010), stories, and security guides to describe email-only flows.
   - Refresh developer onboarding docs (`README.md`, `DEVELOPMENT.md`, `_docs/forms/*.md`, `_docs/guides/security/*.md`) so new contributors are not instructed to create usernames.
   - Ensure `agents.md` or any BMAD stories referencing username/email parity are reconciled with the new direction.

7. **Testing & Validation**

   - Backend: run `pytest` / `python manage.py test --settings=mysite.test_settings` plus targeted suites (`mysite/auth`, `mysite/users`, `mysite/circles`, `mysite/keeps`). Pay special attention to 2FA, OAuth, invitations, and child-upgrade flows.
   - Frontend: run `npm run test` (Vitest) focusing on auth and circles specs; smoke-test forms manually via `npm run start`.
   - End-to-end/local stack: `docker compose up --build` to ensure migrations (even if regenerated later) and API contracts align with the React client.

## Risks & Open Questions

- **Display name replacements:** Large portions of the UI previously surfaced usernames (e.g., circles lists, invitation banners). Decide whether to show email, first+last name, or add a new `display_name` field to avoid exposing raw emails in community contexts.
- **Email uniqueness enforcement:** The new plan assumes every user has a unique email. Confirm this is acceptable for child upgrades or edge cases where emails were optional.
- **Identifier copy:** Password reset, invitation flows, and docs currently promise “username or email” flexibility. Confirm stakeholders accept email-only interactions (especially for circle admins who may not know invitees’ emails).
- **Google OAuth parity:** Newly created Google accounts relied on generated usernames for display and uniqueness. Verify downstream systems (keeps/comments, notifications) do not require those handles and can leverage emails or names provided by Google.
- **Audit & logging noise:** Replacing usernames with emails may expose PII in log lines. Consider masking or using user IDs where appropriate.
- **Timeline for migrations:** Even though migrations are deferred, eventually dropping the `username` column from the database is mandatory. Plan for a `0002_remove_username_from_user` migration before shipping to any shared environments.

---

This plan surfaces every major dependency on usernames so we can implement the switch to email-only authentication methodically and keep backend/frontend/doc artifacts in sync. Once approved, we can proceed with the outlined workstreams, starting with the schema/back-end changes and then iterating across dependent surfaces.

