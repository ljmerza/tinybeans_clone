# Facebook & Apple OAuth Integration Plan

## Overview
- Expand the existing Google OAuth SSO feature set to include Facebook Login and Sign in with Apple across web and mobile-ready APIs.
- Re-use the security posture already in place (state tokens, PKCE, rate limiting, verified email policy) while refactoring to support multiple OAuth providers cleanly.
- Deliver consistent UX on the React client with parity for signup, login, and account linking/unlinking flows.

## Goals
- Support first-party authentication via Facebook and Apple using the Authorization Code + PKCE flow.
- Preserve the account-linking rules currently enforced for Google: auto-link verified accounts, block unverified collisions, and surface clear error messaging.
- Centralize shared OAuth logic to minimize code duplication and simplify adding future providers.
- Ship provider setup guides, troubleshooting runbooks, and updated ADRs/documentation.

## Non-Goals
- Adding native/mobile platform SDK flows (focus is API + web client; mobile apps can adopt once APIs exist).
- Supporting legacy OAuth 1.0 providers or social graph imports.
- Reworking downstream analytics/marketing attribution beyond emitting new auth provider identifiers.

## Current Baseline (Google OAuth)
- Django REST API exposes four endpoints (`/api/auth/google/initiate|callback|link|unlink/`) implemented in `auth/views_google_oauth.py`.
- `GoogleOAuthService` encapsulates PKCE, state tracking via `GoogleOAuthState`, token exchange, and user linking.
- `User` model tracks `google_id`, `google_email`, `auth_provider`, `google_linked_at`, `last_google_sync`.
- Frontend offers a dedicated `GoogleOAuthButton`, hook (`useGoogleOAuth`), callback route, and localized copy.
- Docs: architecture + security analysis under `docs/features/oauth/`, Google Cloud setup guide in `docs/guides/`.

## Implementation Workstreams

### 1. Shared OAuth Foundation
- Extract a provider-agnostic base service (e.g. `OAuthProviderService`) handling:
  - State creation/validation (consider renaming `GoogleOAuthState` to `OAuthState` with provider column + data migration).
  - PKCE generation, rate limit hooks, redirect whitelist enforcement, and error taxonomy.
  - Post-callback orchestration (create/link user, JWT issuance, messaging).
- Introduce provider registry/config to map provider → scopes, endpoints, branding metadata.
- Update DRF serializers to accept `provider` param where appropriate and share validation logic.
- Ensure backwards compatibility for Google routes while enabling new `/api/auth/{facebook|apple}/...` endpoints.

### 2. Facebook OAuth
#### Backend
- Add `facebook_id`, `facebook_email`, `facebook_linked_at`, `last_facebook_sync`, `facebook_access_token_hash` (optional) to `User`.
- Implement `FacebookOAuthService` leveraging the shared base:
  - Use Facebook's OAuth endpoints (`https://www.facebook.com/v18.0/dialog/oauth`, `https://graph.facebook.com/v18.0/oauth/access_token`).
  - Validate `id_token` equivalent by calling `/me?fields=id,email,name,picture` with the access token.
  - Enforce email verification (Facebook may omit `email`; plan for fallback requiring manual email entry/verification).
  - Handle long-lived token exchange if required for profile sync (optional stretch).
- Build DRF views mirroring Google endpoints, apply rate limiting + audit logging.
- Extend admin, Celery cleanup tasks, and metrics (e.g. Prometheus counters per provider).
#### Frontend
- Create `FacebookOAuthButton` + hook with provider-agnostic API client.
- Add callback route `/auth/facebook-callback` reusing shared callback screen logic.
- Update i18n strings, error handling, and account settings UI for linking/unlinking.
#### Provider Setup
- Document Facebook App creation (App ID/Secret, OAuth redirect URIs) and publish in `docs/guides/facebook-app-setup.md`.
- Capture required permissions (likely `email` + `public_profile`) and review submission checklist.

### 3. Apple OAuth
#### Backend
- Extend `User` model with `apple_sub`, `apple_email`, `apple_linked_at`, `last_apple_sync`.
- Implement `AppleOAuthService`:
  - Handle service identifier, team ID, key ID, and private key (stored in secrets manager).
  - Build client assertion JWT to call Apple's token endpoint (`https://appleid.apple.com/auth/token`).
  - Verify identity token using Apple's JWKs (`https://appleid.apple.com/auth/keys`) and enforce nonce validation.
  - Account for private relay emails; require user prompt to share real email before linking if needed.
  - Support re-issuing refresh tokens (Apple returns `refresh_token` only on first exchange; plan secure storage).
- Add endpoints mirroring Google flow with provider-specific serializers where necessary (e.g. Apple requires `user` JSON payload only on first authorization).
- Update settings for Apple credentials (team ID, service ID, key path/secret).
#### Frontend
- Build `AppleOAuthButton` following Apple Human Interface Guidelines (black/white variants, `Sign in with Apple` copy).
- Update callback route `/auth/apple-callback` with logic to handle Apple POST redirect payload (Vite may need Netlify function? For SPA, use `response_mode=form_post` → plan to parse via dedicated API endpoint).
- Update linking UI to surface Apple-specific messaging (e.g. real email sharing).
#### Provider Setup
- Create `docs/guides/apple-sign-in-setup.md` detailing Apple Developer portal steps, redirect URIs, Service ID configuration, and required contracts.

### 4. Configuration & Infrastructure
- Expand `mysite/settings.py` with provider settings (client IDs, secrets, redirect whitelists per provider, scope arrays).
- Update `.env.example` and `docker-compose.yml` with placeholders for new environment variables.
- Ensure secrets management workflow (e.g. Doppler, Vault) can supply Apple private key and Facebook secret securely.
- Add feature flags (`OAUTH_FACEBOOK_ENABLED`, `OAUTH_APPLE_ENABLED`) to gate rollout per environment.
- Update CI/CD to run new tests, lint TypeScript additions, and fail if migrations missing.

### 5. Documentation & Enablement
- Author ADR describing multi-provider OAuth refactor + provider additions.
- Update existing Google docs to reference shared architecture.
- Create runbooks for support (error codes, how to unlink provider, handling Apple relay emails).
- Record QA test matrix and manual test checklist.

## Security & Privacy Considerations
- Maintain strict redirect URI allowlists per provider; add tests for enforcement.
- Persist provider-specific state tokens with IP/User-Agent metadata for audit (GDPR review for retention policy).
- Validate tokens server-side only; never trust frontend-supplied profile data.
- Hash or encrypt any long-lived refresh tokens (Apple) before storage; set rotation/cleanup jobs.
- Ensure unlinking purges stored provider identifiers and refresh tokens.
- Update rate limiting configuration to cover new endpoints.
- Revisit privacy policy/ToS disclosures for additional data sources.

## Testing Strategy
- Unit tests for shared base service and provider-specific services (state validation, token parsing, user linking).
- Integration tests covering happy path + edge cases (missing email, unverified collisions, already-linked accounts).
- Contract tests for DRF serializers to guarantee schema stability (update Spectacular schema if needed).
- Frontend Vitest coverage for hooks/components and Cypress (or Playwright) smoke tests for full flow.
- Staging UAT with real provider credentials behind feature flags before production rollout.

## Rollout Plan & Milestones
1. **Architecture Refactor (Week 1-2)**  
   - Introduce shared OAuth modules, migrations, regression tests for Google.
2. **Facebook Implementation (Week 3-4)**  
   - Backend + frontend flows, documentation, staging validation.
3. **Apple Implementation (Week 5-6)**  
   - Backend + frontend flows, secure key management, staging validation.
4. **Launch Prep (Week 7)**  
   - Feature flag dry run, support training, final documentation updates.

Timelines assume 1-2 engineers with alternating backend/frontend focus; adjust based on staffing.

## Open Questions & Dependencies
- Do we need separate redirect URIs for web vs mobile clients?
- How will mobile apps consume the new endpoints (deep link strategy, PKCE support)?
- Should we unify login buttons into a single configurable component set?
- Does product want to require email disclosure when Apple returns a private relay address?
- Any legal review required for Facebook permissions beyond basic profile?
- Confirm analytics events/schema changes (e.g. Segment `auth_provider` values).

## Success Metrics
- % of new signups via Facebook/Apple within 30 days of launch.
- Reduction in support tickets related to login issues.
- OAuth error rate per provider < 1% of total attempts.
- Time-to-link for existing users stays under current baseline (< 5s median).

## Required Updates After Implementation
- `.env.example`, `.env`, `docker-compose.yml`, and deployment secrets.
- DRF Spectacular schema + Postman collection (if maintained).
- `docs/features/oauth/` architecture & security docs.
- Onboarding playbooks, marketing site copy (if listing new login options).
