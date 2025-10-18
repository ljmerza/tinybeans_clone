# Epic: Circle Invite Modernization

- Status: Draft
- Owner: Core platform team
- Source PRD: `docs/prd.md` (Epic 1)
- Related ADRs: `docs/adrs/0001-circle-invite-flow.md`

## Overview
Modernize the Tinybeans Circles invitation experience so admins can invite by username or email, invitees explicitly accept before joining, and onboarding respects the existing auth stack (magic link, Google OAuth, 2FA). The epic coordinates backend, frontend, and notification updates while maintaining backward compatibility with the legacy email-only flow.

## Goals & Success Metrics
- Admins send invites using either username or email with clear status feedback.
- Invitation lifecycle (pending/accepted/declined/expired) is auditable and visible in the UI.
- New invitees complete onboarding through established authentication flows without regressions.
- Invitation abuse is mitigated through rate limiting and token TTL configuration.
- Frontend and backend test suites cover happy paths and edge cases for invitations.

## Non-Goals
- Redesigning broader circle management UX beyond invitations.
- Overhauling the entire authentication system (only integration points are touched).
- Introducing new external identity providers.

## Dependencies
- Existing authentication services (`mysite/auth`) for magic link, OAuth, 2FA, and token utilities.
- Notification infrastructure (emails, Celery workers) for invite-related messaging.
- React circles feature area (`web/src/features/circles`) for UI integration.

## Risks & Mitigations
- **Auth regression risk**: Strengthen automated tests covering token issuance/validation and invite acceptance paths.
- **Data migration risk**: Stage Django migrations with backups and dry-run options; maintain backward-compatible schemas.
- **UX inconsistency risk**: Reuse shared components and design tokens; align with upcoming design refresh documentation.

## Story Breakdown
1. **Backend Support for Username-Aware Invites**  
   - Extend DRF endpoints to accept username/email, keep invites pending, enforce rate limits, and surface status metadata.  
   - Update serializers, tasks, and tests in `mysite/users`.

2. **Onboarding Flow for New Invitees**  
   - Generate onboarding tokens tied to invitations, integrate with magic link/OAuth/2FA flows, and finalize membership upon acceptance.  
   - Enhance notification workflows and Celery tasks.

3. **Frontend Admin Invitation Experience**  
   - Add invite modal/list components, status tracking, and resend/cancel controls using TanStack Query.  
   - Ensure responsive UX and error handling via shared components.

4. **Invitee Onboarding UX and Notifications**  
   - Implement React flows for acceptance/decline/expired states, deliver confirmation toasts/emails, and log funnel analytics.  
   - Verify build/lint/test pipelines remain green.

## Definition of Done
- All stories implemented with passing pytest/Vitest suites and updated drf-spectacular schema.  
- Documentation updated: ADR 0001, PRD, environment samples, and any new ADRs spawned by implementation details.  
- Operational runbooks describe rate-limit settings, invite token TTLs, and rollback procedures for migration issues.
