# First-Login Circle Onboarding Plan

## Overview
- **Goal:** Automatically guide first-time authenticated users through creating their own circle, while allowing them to cancel and continue to the home experience.
- **Scope:** Backend API updates for onboarding state tracking, frontend routing/UI for the creation flow, and supporting analytics/tests.
- **Out of scope:** Broader circle management UX, invitation flows, or long-term reminders for users who skip onboarding.

## Current State (Baseline)
- `POST /auth/login/` returns user details + access token but no onboarding metadata.
- `CircleCreateSerializer` requires verified email and automatically assigns the creator as a circle admin.
- Frontend auth flow (`useLogin`) always navigates to `/` after a successful login.
- No dedicated UI or route for circle creation; i18n strings exist but no components are wired up.

## Target User Flow
1. **Login Success (no 2FA):** API signals `needsCircleOnboarding = true` when the authenticated user has never logged in and has no circle memberships.
2. **Redirect:** Frontend navigates to `/circles/onboarding` instead of `/`.
3. **Circle Setup Page:**
   - Displays a short explainer and form to name the user’s first circle.
   - Detects unverified email status and prominently prompts verification (with resend link) instead of blocking access to the rest of the app.
   - Includes a `Skip for now`/`Not now` button that returns the user to the home screen, even if they’re unverified.
4. **Success Path:** On creation, mark onboarding complete server-side and send the user to the new circle (if a detail page exists) or back to `/` with success messaging.
5. **Cancel Path:** Skipping records dismissal in the backend, suppressing further forced redirects, and returns the user to `/`.
6. **Subsequent Sessions:** Normal navigation; no forced redirects once onboarding is completed or dismissed. Future nudges (banners, etc.) are future work.

## Backend Plan
- **Data Model**
  - Add `circle_onboarding_status` (`pending` | `completed` | `dismissed`) + optional `circle_onboarding_updated_at` to `users.User`.
  - Default to `pending`; data migration sets to `completed` for users with existing memberships or non-null `last_login`.
- **Login Response**
  - Include `needs_circle_onboarding` boolean and `circle_onboarding_status` string in the serialized payload.
  - Compute `needs_circle_onboarding` as `status == pending` and user has zero memberships.
  - Ensure 2FA and trusted-device branches align with this payload shape.
- **Circle Lifecycle Hooks**
  - When a user creates a circle or gains a membership (creator or inviter acceptance), set status to `completed`.
  - When a user explicitly skips onboarding, set status to `dismissed`.
- **Email Verification Delivery**
  - Ensure signup continues to trigger the verification email automatically (already implemented) and log failures so onboarding UI can surface resend guidance.
- **Endpoints**
  - `GET /users/circle-onboarding/` → `{ status, needs_circle_onboarding, memberships_count }`.
  - `POST /users/circle-onboarding/skip/` → marks dismissed.
  - (Optional) `POST /users/circle-onboarding/reset/` for admin/debug use; keep behind staff permissions.
  - Tighten serializers to return useful error codes (e.g., email verification required) so UI can react.
- **Migrations & Signals**
  - Data migration to backfill existing users.
  - Consider post-save signal on `CircleMembership` to auto-complete onboarding if still pending.
- **Tests**
  - Model tests for new status field + transitions.
  - Login API tests covering flag values (first login, returning user, invited member).
  - Circle creation tests asserting onboarding completion side effects.
  - Skip endpoint authorization + idempotency tests.

## Frontend Plan
- **Auth Types & Store**
  - Extend `AuthUser`/`LoginResponse` to include `circleOnboardingStatus` and `needsCircleOnboarding`.
  - Update `useLogin` success handler to branch based on flag before navigating.
- **Routing**
  - Add route `web/src/routes/circles/onboarding.tsx` + matching entry in `route-views`.
  - Introduce loader/action hooks to fetch onboarding status (reuse after refresh or deep links).
- **UI Components**
  - Build `CircleOnboardingLayout` with explainer copy, status badges, and `Skip` CTA.
  - Implement `CircleCreateForm` reusing shared form primitives (`FormField`, `Input`, `FormActions`).
  - Show inline error when email verification is required, surfacing CTA to resend verification (existing endpoint).
  - Provide a shared resend verification affordance surfaced both here and within the profile/settings email section so users can trigger it from either context.
- **State Handling**
  - On success → invalidate `authKeys.session()` and `userKeys` data, then navigate to `/` (or new circle route once available).
  - On skip → call skip endpoint, update local state, and navigate to `/`.
  - Guard route so authenticated users with status `completed`/`dismissed` are redirected away (prevents bookmarking misuse).
- **UX Details**
  - Provide loading skeleton/states while fetching onboarding status.
  - Ensure toast messaging uses i18n keys returned by backend.
  - Maintain accessibility: autofocus on first input, semantic headings, ARIA for error summary.

## Edge Cases & Open Questions
- **Invited Users:** If an invited user’s first login already grants membership, skip onboarding automatically (`needs_circle_onboarding = false`).
- **Email Verification Gate:** Do not hard-block login for unverified users. Keep the onboarding redirect, but if `email_verified` is false show the circle page in a “pending verification” state with resend CTA and a Skip button so they can continue using the app until verification completes.
- **Multiple Devices:** Ensure skip/completion state is server-tracked so status stays consistent across devices.
- **Future Nudges:** Requirement does not specify re-prompt cadence after skip; treat skip as “don’t force redirect again” but document possibility of future banner reminders.
- **Verification Window Sync:** After the user triggers a resend or clicks the verification link in another tab, poll or provide a manual "I’ve verified" button to refresh status without forcing a full logout/login.
- **Resend Rate Limits:** Surface messaging when verification resends are throttled so the user understands why the button is disabled.
- **2FA Intersection:** Ensure the flow still works when login returns the intermediate 2FA step—once 2FA is cleared we should re-evaluate onboarding flags before redirecting.
- **Session Expiry While Onboarding:** If the refresh token expires mid-flow, make sure the user returns to login with a helpful message instead of a generic error page.
- **Admin-Assigned Circles Pre-Login:** Handle cases where ops adds users to circles before their first login so onboarding skips automatically but still celebrates the membership.

## UX Enhancements
- Provide a short step indicator (e.g., "Step 1 of 2: Create your circle") so the user understands the broader onboarding journey.
- Keep the Skip button visible at all scroll positions (sticky footer or duplicated near the top) to avoid accidental entrapment.
- Offer contextual tips or examples under the circle-name field (e.g., "Smith Family") to reduce blank submissions.
- Use a non-blocking success toast plus inline confirmation before redirecting to reinforce that the circle was created.
- For mobile, ensure the layout keeps critical actions above the fold and keyboards don’t hide error messages.

## Open Questions & Proposed Answers
- **Future Nudges:** Show a dismissible home-banner once per week for users who dismissed onboarding, controlled by server-side status + last_prompt timestamp.
- **Verification Window Sync:** Add a `Check verification` button that calls `/users/circle-onboarding/` and optionally auto-polls every 30 seconds for five minutes after a resend.
- **Resend Rate Limits:** When the backend returns `retry_after`, render a countdown timer and disable the resend button until it elapses.
- **2FA Intersection:** Persist the intended post-login redirect (`/circles/onboarding`) in router state so once 2FA succeeds we still reroute through the onboarding guard.
- **Session Expiry While Onboarding:** Centralize 401 handling to show a modal explaining the session expired with a direct link back to `/login?redirect=/circles/onboarding`.
- **Admin-Assigned Circles Pre-Login:** If the onboarding guard sees memberships but status is still `pending`, auto-mark complete yet show a toast celebrating their first circle.
- **Copy & Localization:** Coordinate new strings (`onboarding.firstCircle.title`, etc.) with the localization pipeline to prevent untranslated screens at launch.

## Implementation Steps
1. **Backend**
   - Add model field + migration (including data backfill).
   - Expose onboarding flags in login response + new `/users/circle-onboarding/` endpoints.
   - Update circle creation & membership flows to finalize onboarding.
   - Write unit/integration tests.
2. **Frontend**
   - Update auth types/hooks to read new fields.
   - Create onboarding route + components + skip handler.
   - Wire form submission to `POST /users/circles/` and handle success/blocked states.
   - Add route guards + tests (Vitest/components).
3. **QA**
   - Manual test matrix: new signup, invited user, skip path, email unverified scenario, returning user.
   - Verify translations + toasts.
4. **Docs & Rollout**
   - Update user onboarding documentation (this doc + README snippet).
   - Communicate migration impact (new nullable field) to ops.

## Risks & Mitigations
- **Login Payload Changes:** Coordinate frontend + backend deploys; feature-flag backend field behind tolerant parsing (`??` checks).
- **Blocking Users Without Verified Email:** Ensure skip path remains available and messaging explains requirements.
- **Data Backfill Accuracy:** Validate migration by spot-checking users with/without memberships; add SQL fallback script if counts are large.
