# Frontend Component Refactor Plan

This document outlines architecture improvements for several frontend components that currently mix data orchestration, side effects, and rendering logic. The goal is to isolate domain logic into reusable hooks and utilities so the view layer stays declarative and easy to test.

## CircleInvitationList (`web/src/features/circles/components/CircleInvitationList.tsx`)

- **Problem**: The component owns query wiring, mutation orchestration, normalization utilities, and confirmation dialog logic, resulting in 450+ lines of tightly coupled UI and side effects.
- **Plan**
  - Introduce `useCircleInvitationActions(circleId)` that fetches invitations, returns sorted data, and exposes `resend`, `cancel`, and `remove` handlers with loading flags.
  - Lift helper functions (`normalizeId`, `describeTimestamp`, `findMemberId`) into `features/circles/utils/invitations.ts`.
  - Convert the component into a presentational `CircleInvitationList` that accepts `{ invitations, status, actions }`.
  - Add hook unit tests covering member resolution, refetch fallback, and failure states.

## InvitationAcceptContent (`web/src/route-views/invitations/accept.tsx`)

- **Problem**: A single component manages the entire invitation acceptance state machine, local storage syncing, redirects, and mutation side effects via multiple `useEffect` blocks and refs.
- **Plan**
  - Build `useInvitationAcceptance(token)` that encapsulates onboarding token tracking, subscription to `invitationStorage`, and acceptance/decline mutations.
  - Replace the current ref-based flow with a local reducer or explicit state machine to document transitions (`loading → pending → finalizing → accepted/declined/error`).
  - Render UI through a `InvitationAcceptScreen` presentational component receiving the state snapshot and action callbacks.
  - Provide hook tests that stub storage and navigation to verify retry, auto-finalize, and redirect paths.

## CircleOnboardingContent (`web/src/route-views/circles/onboarding.tsx`)

- **Problem**: Form validation, refresh polling, toast notifications, and navigation live in the same component as the view markup; stray console usage leaks implementation details.
- **Plan**
  - Extract `useCircleOnboardingController()` to coordinate `useCircleOnboardingQuery`, resend, skip, and create actions while surfacing derived booleans and messages.
  - Split the view into subcomponents (`CircleOnboardingCallout`, `CircleOnboardingForm`, etc.) that consume controller props.
  - Remove console statements; use the controller to trigger toasts and errors.
  - Add unit tests for controller edge cases: unverified email refresh, skip failures, and validation errors.

## TwoFactorSettingsPage (`web/src/routes/profile/2fa/index.tsx`)

- **Problem**: The route file mixes query handling, mutation state, modal visibility, and rendering of all method cards, making it difficult to test or reuse pieces.
- **Plan**
  - Implement `useTwoFactorSettings()` returning `{ status, modalState, errors, actions }` to encapsulate preferred method updates and removal workflows.
  - Break JSX into smaller presentational pieces (`TwoFactorMethodsPanel`, `TwoFactorMethodList`, `TwoFactorRemovalDialog`), each receiving simple props.
  - Keep method cards pure and memoizable by pushing side effects into the hook.
  - Cover the hook with tests that simulate happy paths and API failures for switching/removing methods.

## Suggested Execution Order

1. Circle invitations: hook extraction, utility module, and tests.
2. Invitation acceptance: state machine refactor and presentational split.
3. Circle onboarding: controller hook and component decomposition.
4. Two-factor settings: hook + panel split and supporting tests.

Each milestone reduces surface area for regression, enabling incremental merges without blocking daily work.
