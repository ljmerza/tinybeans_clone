# Tinybeans Circles Brownfield Enhancement PRD

## Intro Project Analysis and Context

### Existing Project Overview
**Analysis Source**  
IDE-based fresh analysis (referencing `docs/brownfield-architecture.md` for technical detail).

**Current Project State**  
Tinybeans Circles is a Tinybeans-inspired platform where users gather in “circles” to share photos, videos, notes, and comments. The backend lives in `mysite/` (Django REST, Celery, Redis) with domain apps for auth, users, keeps, messaging, and emails. The frontend is a React 19/Vite/TanStack application in `web/`, and `docker-compose.yml` orchestrates Django, Postgres, Redis, Celery workers/beat, Flower, Mailpit, MinIO, pgAdmin, RedisInsight, and the Vite dev server. Authentication spans magic links, Google OAuth, 2FA, recovery codes, and trusted devices—making it the most intricate surface in the current system.

### Available Documentation Analysis
Using existing project analysis from `docs/brownfield-architecture.md` (generated via document-project reset).

- [x] Tech Stack Documentation  
- [x] Source Tree/Architecture  
- [ ] Coding Standards (to be rebuilt)  
- [x] API Documentation (via drf-spectacular + architecture doc references)  
- [ ] External API Documentation (Google/Twilio still needs refresh)  
- [ ] UX/UI Guidelines (design tokens slated for rebuild)  
- [x] Technical Debt Documentation  
- Other: Documentation reboot underway in `docs/`

### Enhancement Scope Definition
**Enhancement Type**
- [x] New Feature Addition
- [x] Major Feature Modification
- [ ] Integration with New Systems
- [ ] Performance/Scalability Improvements
- [ ] UI/UX Overhaul
- [ ] Technology Stack Upgrade
- [ ] Bug Fix and Stability Improvements
- Other: —

**Enhancement Description**  
Introduce a robust invite flow that lets circle admins invite by username or email, sends existing users an acceptance email, gracefully onboards new users when accounts do not yet exist, and keeps all flows aligned with the complex auth surface (magic link, Google OAuth, 2FA).

**Impact Assessment**
- [ ] Minimal Impact (isolated additions)
- [x] Moderate Impact (some existing code changes)
- [x] Significant Impact (substantial existing code changes)
- [ ] Major Impact (architectural changes required)

### Goals and Background Context
**Goals**
- Circle admins can add members via username or email without leaving the app.
- Existing users receive invitation emails and accept before joining the target circle.
- Invitees without accounts follow an onboarding path that respects magic-link, Google OAuth, and 2FA flows.
- Invitation lifecycle is auditable for support/debugging.
- Rate limiting and abuse controls protect the system as sharing expands.

**Background Context**  
Tinybeans Circles reimagines the Tinybeans family-sharing experience for broader social circles. Current circle membership relies on email-only invites with manual onboarding, which clashes with the richer identity surface and security measures already built. Admins need a dependable way to invite both existing and new users while maintaining explicit acceptance, audit trails, and consistent notification coverage.

The invite modernization introduces username search, onboarding handoffs for new accounts, and stronger status/notification feedback so backend services and the React UI stay synchronized across acceptance, decline, or expiration.

### Change Log
| Change | Date | Version | Description | Author |
| --- | --- | --- | --- | --- |
| Initial draft | 2025-02-14 | 0.1 | Captured current architecture, goals, and scoped circle invite enhancement | BMad Master |

## Requirements

**Functional Requirements**  
- FR1: Circle admins must invite members by entering either a username or email and see whether the target already exists.  
- FR2: When the invitee already has an account, the system must create a pending circle invitation, notify them via existing channels, and only convert them to a member after acceptance.  
- FR3: When the invitee lacks an account, the system must generate a pending user onboarding token that honors existing magic-link, Google OAuth, and 2FA enrollment flows before granting circle access.  
- FR4: Circle admins must retrieve real-time invite status (pending, accepted, declined, expired) via REST endpoints and use this data to resend or cancel invites.  
- FR5: The system must send transactional notifications (email and in-app) for invitations, acceptance, decline, or expiration using existing Celery queues and templates.
- FR6: Invitation onboarding success must notify circle admins so they can track membership changes.
- FR7: Invitation workflows must enforce configurable rate limits per admin and per circle to mitigate abuse.

**Non-Functional Requirements**  
- NFR1: Enhanced invite flows must reuse existing auth safeguards (magic-link TTLs, 2FA enrollment, Google OAuth validations) without weakening security posture.  
- NFR2: New API endpoints must respond within current performance thresholds (<300 ms p95 under nominal load) and offload slower work to Celery.  
- NFR3: Invite creation must be idempotent for the same admin→target pairing to avoid duplicate invitations or memberships.  
- NFR4: Invitation data must remain auditable, retaining status history and inviter metadata for at least 30 days.  
- NFR5: Frontend UX must gracefully recover from backend failures, displaying actionable error messages without exposing internal details.

**Compatibility Requirements**  
- CR1: Existing email-based invitation endpoints remain available and continue producing pending invites requiring acceptance.  
- CR2: Database migrations must preserve existing invitation and membership records without requiring data backfills or downtime.  
- CR3: Updated UI must retain current navigation patterns and component styling so the circles experience stays consistent.  
- CR4: Integrations with notification services, Celery workers, and Redis token storage must keep working without configuration changes.

## User Interface Enhancement Goals

**Integration with Existing UI**  
Invites live inside the existing circles management flow (`web/src/features/circles`), reusing shared Radix/Tailwind components from `web/src/components`. Search inputs, badges, and call-to-action buttons leverage existing `Input`, `Button`, and `Badge` primitives to preserve styling.

**Modified/New Screens and Views**  
- Circles admin invite modal/panel with username/email search.  
- Pending invitation list with status filters and actions.  
- Onboarding/acceptance screens for invitees entering via magic link or OAuth callbacks.  
- Toast notifications confirming success/error states.

**UI Consistency Requirements**  
- Maintain typography and spacing tokens defined in `web/components.json`.  
- Reuse toast patterns from `web/src/components/toast`.  
- Keep admin workflows within the circles route to avoid context switching.  
- Apply existing `EmptyState` and `Skeleton` components for empty/loading states.

## Technical Constraints and Integration Requirements

**Existing Technology Stack**  
**Languages**: Python 3.12, TypeScript 5.7, JavaScript (ES2023), SQL (PostgreSQL), HTML/CSS (Tailwind tokens)  
**Frameworks**: Django 5.2.6 + DRF, Celery 5.4, React 19 (Vite 7), TanStack Router/Query/Form, Radix UI + Tailwind 4  
**Database**: PostgreSQL 16 (primary), Redis 7 (cache/broker), MinIO (S3-compatible storage)  
**Infrastructure**: Docker Compose stack (Django API, Celery workers/beat, Flower, PostgreSQL, Redis, Mailpit, MinIO, pgAdmin, RedisInsight, Vite dev server); production target AWS ECS/Fargate + RDS + ElastiCache + S3/CloudFront  
**External Dependencies**: Google OAuth 2.0, Twilio SMS (optional), Mailpit, drf-spectacular, Celery email templates, pyotp, Redis token store

**Integration Approach**  
**Database Integration Strategy**: Extend `CircleInvitation` via Django migrations (support username/email metadata, unique constraints), reuse Redis token store for onboarding links, ensure historic invites remain intact.  
**API Integration Strategy**: Enhance `mysite/circles/views/` and serializers to support username-aware invitations, explicit acceptance endpoints, and status management.  
**Frontend Integration Strategy**: Add invite mutations and list queries using TanStack Query in `web/src/features/circles`, new onboarding views under `web/src/routes`, and shared UI components for consistent feedback.  
**Testing Integration Strategy**: Pytest coverage in `mysite/users/tests`, Celery task tests for notifications, DRF schema validation, and Vitest specs for new React flows—including invite acceptance edge cases.

**Code Organization and Standards**  
**File Structure Approach**: Backend changes stay within `mysite/users` (views, serializers, tasks, migrations) and supporting auth utilities; frontend logic remains scoped to `web/src/features/circles` with routes and components colocated.  
**Naming Conventions**: Continue PEP 8 module naming, PascalCase for Django models/React components, and camelCase for hooks/functions; keep `CircleInvitation*` prefixes consistent.  
**Coding Standards**: Follow PEP 8, DRF serializer patterns, Celery idempotency, Ruff linting goals, and strict TypeScript with Biome lint/format.  
**Documentation Standards**: Update `docs/brownfield-architecture.md`, capture decisions in new ADRs, annotate API changes via drf-spectacular, and refresh frontend design docs once component tokens are rebuilt.

**Deployment and Operations**  
**Build Process Integration**: Reuse Dockerfile/Compose; ensure `docker compose up --build` applies migrations and seeds data; front-end builds with `npm run build`.  
**Deployment Strategy**: Roll out backend/worker containers through the existing pipeline (Docker/ECS); run migrations before deploying invite UI; ship frontend bundles to CDN/static hosting.  
**Monitoring and Logging**: Extend structured logging to capture invite lifecycle events; monitor Celery queues via Flower; plan Sentry integration for production.  
**Configuration Management**: Add env flags for invite rate limiting, onboarding token TTL, and reminder cadence/batch sizing in `.env.example`; document Google OAuth/Twilio secrets in `DEVELOPMENT.md`.

**Risk Assessment and Mitigation**  
**Technical Risks**: Expanded flows could introduce auth bypasses or inconsistent invitation states; Redis token TTLs must align with onboarding windows.  
**Integration Risks**: Misalignment with existing magic-link/2FA flows may regress login; frontend must handle both username and email gracefully.  
**Deployment Risks**: Migrations might disrupt current pending invites if not staged; API adjustments could surprise clients relying on legacy responses.  
**Mitigation Strategies**: Maintain backward-compatible endpoints, dry-run migrations, comprehensive testing across happy/edge paths, and clear rollout documentation (including rollback procedures).

## Epic and Story Structure

**Epic Structure Decision**: Single epic covering backend + frontend invite modernization because invite onboarding touches tightly coupled services (users/auth/notifications/UI), and sequencing within one epic simplifies dependency management and rollback safety.

### Epic 1: Circle Invite Modernization

**Epic Goal**: Deliver a unified invite experience that lets circle admins add members by username or email while preserving existing auth safeguards and explicit acceptance.

**Integration Requirements**: Coordinate Django invite APIs, Redis token storage, Celery notifications, and React onboarding views so both existing and new users reach the circle without regressing magic-link/2FA/OAuth flows.

#### Story 1.1 Backend Support for Username-Aware Invites
As a circle admin, I want to invite members by username or email with clear feedback, so that I can quickly add existing community members without guesswork.

**Acceptance Criteria**  
1. API accepts either username or email and indicates whether the target user already exists.  
2. Invites always persist as pending until recipients explicitly accept; membership links are created only after acceptance.  
3. API responses include structured status codes/messages surfaced by drf-spectacular schema updates.  
4. Rate limiting guards against invite spam per admin and per circle, configurable via settings.

**Integration Verification**  
IV1. Legacy email invite POST endpoints continue to function, producing pending invites that require acceptance.  
IV2. Redis token storage issues/validates invite tokens alongside magic-link tokens without conflict.  
IV3. API latency stays within existing p95 budget (<300 ms) under load.

#### Story 1.2 Onboarding Flow for New Invitees
As an invited user without an account, I want a guided onboarding path that honors existing auth options, so that I can join a circle securely and finish setup without friction.

**Acceptance Criteria**  
1. New invite flow generates onboarding tokens tied to invitation metadata with expiration management.  
2. Magic link, Google OAuth, and 2FA enrollment steps integrate seamlessly before circle membership is finalized.  
3. Invite status transitions to “accepted” only after the onboarding/auth journey completes (same rule as existing users).  
4. Notification templates for onboarding and reminders queue through existing Celery workers.

**Integration Verification**  
IV1. Non-invite login flows remain unchanged.  
IV2. Redis token cleanup handles magic-link, invite, and onboarding tokens without collisions.  
IV3. Celery worker throughput stays within current thresholds.

#### Story 1.3 Frontend Admin Invitation Experience
As a circle admin using the web app, I want an intuitive invite UI with status tracking, so that I can manage invitations without leaving the circles dashboard.

**Acceptance Criteria**  
1. Invite modal/panel allows searching by username/email, displaying existence state and validation errors.  
2. Pending invitation list surfaces statuses (pending, accepted, declined, expired) with resend/cancel controls.  
3. UI leverages shared components (Button, Input, Badge, Toast) in line with design tokens.  
4. Error handling provides actionable messages without exposing backend details.

**Integration Verification**  
IV1. Circles management screens render unchanged when the invite feature toggle is off.  
IV2. TanStack Query cache invalidation keeps invite/member lists synchronized.  
IV3. Lighthouse performance scores for the circles route stay at their prior baseline.

#### Story 1.4 Invitee Onboarding UX and Notifications
As an invitee responding to an invite, I want a clear onboarding/acceptance experience, so that I know when I’ve joined the circle and what to do next.

**Acceptance Criteria**  
1. React onboarding flow handles magic-link and OAuth callbacks, prompting for 2FA where required.  
2. Pending/accepted/declined/expired paths each show distinct screens following existing UX patterns.  
3. Toasts and emails confirm acceptance or decline; admins receive in-app notifications when invite status changes.  
4. Analytics/logging capture invite acceptance funnel events for future metrics.

**Integration Verification**  
IV1. Invite acceptance never bypasses 2FA enforcement when enabled.  
IV2. Email templates render correctly through Mailpit in dev and through production mail providers.  
IV3. `npm run build` passes with no new type or lint issues.

This story sequence is designed to minimize risk to your existing system. Let me know if any adjustments are needed.
