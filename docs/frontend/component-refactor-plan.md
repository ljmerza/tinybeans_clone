# Frontend Component Refactor Plan

This document outlines architecture improvements for several frontend components that currently mix data orchestration, side effects, and rendering logic. The goal is to isolate domain logic into reusable hooks and utilities so the view layer stays declarative and easy to test.

## CircleInvitationList (`web/src/features/circles/components/CircleInvitationList.tsx`)

- **Status**: ✅ Completed — controller hook + item component shipped.
- **Problem**: The component owned query wiring, mutation orchestration, normalization utilities, and confirmation dialog logic, resulting in 450+ lines of tightly coupled UI and side effects.
- **Resolution**
  - Added `useCircleInvitationListController(circleId)` to encapsulate fetching, sorting, and mutation state.
  - Moved helper functions (`normalizeId`, `describeTimestamp`, `findMemberId`) into `features/circles/utils/invitationHelpers.ts`.
  - Split each row into `CircleInvitationListItem`, keeping the list presentational.
  - Supplemented with controller hook tests covering member resolution and mutation flows.

## InvitationAcceptContent (`web/src/route-views/invitations/accept.tsx`)

- **Status**: ✅ Completed — dedicated hook and lighter view now in place.
- **Problem**: A single component managed the entire invitation acceptance state machine, local storage syncing, redirects, and mutation side effects via multiple `useEffect` blocks and refs.
- **Resolution**
  - Implemented `useInvitationAcceptance` to handle storage sync, mutations, navigation, and transition guards.
  - Kept `InvitationAcceptContent` as a thin presenter consuming the hook’s derived state.
  - Added hook-focused tests to simulate autFinalize, redirect, and unauthenticated flows.
  - Updated the route test to exercise the view with mocked hook state.

## TwoFactorSettingsPage (`web/src/routes/profile/2fa/index.tsx`)

- **Status**: ✅ Completed — controller hook plus modular components added.
- **Problem**: The route file mixed query handling, mutation state, dialog visibility, and rendering of the method cards, making the view difficult to test or reuse.
- **Resolution**
  - Introduced `useTwoFactorSettings()` to own status loading, mutations, and error state.
  - Added `TwoFactorSettingsContent` and `TwoFactorRemovalDialog` to isolate the UI logic.
  - Simplified the route to layout wiring only and backed the hook with focused unit tests.

## CircleOnboardingContent (`web/src/route-views/circles/components/CircleOnboardingContent.tsx`)

- **Status**: ✅ Completed — controller hook added and content simplified.
- **Problem**: Form validation, refresh polling, toast notifications, and navigation lived in the same component as the view markup, obscuring behavior.
- **Resolution**
  - Added `useCircleOnboardingController()` to own form submission, skip/resend flows, and refresh handling.
  - Reused the hook inside the route view, leaving the component mostly presentational.
  - Preserved the existing layout while making resend/skip logic testable via dedicated hook specs.

## Suggested Execution Order

All listed refactors are complete. Move on to new architectural work as needed.

Each milestone reduces surface area for regression, enabling incremental merges without blocking daily work.
