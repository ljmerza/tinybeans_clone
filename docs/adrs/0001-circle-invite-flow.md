# ADR 0001: Circle Invitation Flow Modernization

- Status: Accepted
- Date: 2025-02-14
- Related Artifacts: `docs/prd.md`, `docs/brownfield-architecture.md`

## Context
- Tinybeans Circles intentionally relies on email-only invitations to keep authentication aligned with the broader email-only identity plan.
- Authentication is multi-surface (magic link, Google OAuth, 2FA, recovery codes, trusted devices) and must stay consistent when onboarding invited users.
- Admins need visibility into invitation status and safeguards against abuse as circles expand.
- Documentation has been rebooted in `docs/`, requiring new canonical records for architectural decisions.

## Decision
Adopt an email-only invitation system where circle admins invite by email, always generating a pending invitation. Existing users receive acceptance emails and join only after explicit confirmation; new users receive onboarding tokens that guide them through the existing auth stack (magic link, OAuth, 2FA) before finalizing membership. All invitation events feed existing notification channels (email, in-app) and are auditable, with rate limiting enforced per admin and circle.

## Rationale
- Respects current security posture by keeping explicit acceptance even for known users.
- Aligns backend (`mysite/users`) and frontend (`web/src/features/circles`) enhancements under a single epic for easier sequencing and rollback.
- Supports future analytics by capturing invitation lifecycle events in structured logs.
- Provides a foundation for AI agents to implement invite-related stories without consulting deprecated `_docs/`.

## Consequences
- Requires Django migrations to extend `CircleInvitation` metadata and DRF endpoint adjustments.
- Demands React updates for invite creation, status tracking, and invitee onboarding experiences.
- Introduces configuration for rate limits and token TTLs that must be documented in `.env.example` and deployment runbooks.
- Adds testing obligations across pytest (backend) and Vitest (frontend), plus Celery integration coverage.

## Alternatives Considered
- **Immediate auto-join for existing users**: Rejected to preserve explicit consent and auditability.
- **Dual-identifier invites (username or email)**: Rejected to keep identity consistent and avoid reintroducing username behaviors removed elsewhere.
- **Deferring modernization to a future release**: Rejected because invite usability is foundational for circle adoption and future features rely on these enhancements.
