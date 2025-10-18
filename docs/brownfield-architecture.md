# Tinybeans Circles Brownfield Architecture Document

## Introduction
This document captures the current-state architecture of the Tinybeans Circles project—a Tinybeans-inspired platform where users participate in “circles” to share photos, videos, notes, and comments. It maps the live Django + React system, highlights technical debt and quirks, and serves as the starting point for future ADRs in the rebuilt `docs/` directory.

## System Snapshot
- **Repository Layout**: Monorepo with Django backend in `mysite/` and React 19 frontend in `web/`
- **Primary Domains**: Circles & membership (`mysite/users`), keeps/media (`mysite/keeps`), messaging/notifications (`mysite/messaging`, `mysite/emails`)
- **Identity Surface**: Multi-mode auth featuring magic links, Google OAuth, 2FA, recovery codes, and trusted devices (`mysite/auth`)
- **Async Workloads**: Celery workers sharing Redis for brokerage and caching; scheduled tasks executed via Celery beat
- **Invitation Onboarding**: Dual-step flow using Redis-backed onboarding tokens (`circle-invite-onboarding`) with configurable TTL, plus Celery email notifications for reminders and acceptance
- **Local Orchestration**: `docker-compose.yml` bootstraps Django, Postgres, Redis, Mailpit, MinIO, pgAdmin, Celery workers/beat, Flower, and the Vite dev server
- **Documentation Reset**: Legacy `_docs/` artifacts are superseded; this file inaugurates the new `docs/` tree and becomes the baseline for subsequent ADRs

## Repository Structure
```
tinybeans_copy/
├── docs/                     # New documentation root (this file)
├── mysite/                   # Django project root (manage.py, apps, Celery config)
│   ├── auth/                 # Authentication domain (magic link, Google OAuth, 2FA)
│   ├── keeps/                # Keeps (moments), media attachments, milestones
│   ├── messaging/            # In-app messaging, notifications, email orchestration
│   ├── users/                # User profiles, circles, onboarding, serializers
│   └── mysite/               # Django project package (settings, URLs, Celery app)
├── web/                      # React 19 + Vite frontend
│   ├── src/components/       # Shared UI components (Radix + Tailwind)
│   ├── src/features/         # Feature modules (auth, circles, keeps, etc.)
│   ├── src/routes/           # TanStack Router route definitions
│   └── src/lib/              # API clients, hooks, utility helpers
├── docker-compose.yml        # Local stack orchestration (backend, frontend, infra)
├── Dockerfile                # Backend/worker image
├── requirements.txt          # Python dependencies (Django 5.2.6, Celery 5.4, etc.)
└── README.md                 # Quick-start commands and TODO list
```

## Backend Architecture (Django)
### Project Configuration
- **Settings**: Modular settings under `mysite/mysite/config/settings/` with `base.py` shared across environments (local, staging, production, test). Environment variables are consumed via helper functions for flags/lists/ints.
- **Celery**: Configured in `mysite/mysite/celery.py` with queues for email, SMS, media, and maintenance. Beat schedules are defined in settings and seeded through Docker entrypoints.
- **Logging**: Centralized configuration in `mysite/mysite/logging.py` with per-service loggers used across apps.

### Core Apps
| App | Responsibility | Key Modules |
| --- | -------------- | ----------- |
| `mysite/auth` | Authentication flows (passwordless magic links, Google OAuth, 2FA, trusted device management, recovery codes, rate limiting) | `views.py`, `views_google_oauth.py`, `views_2fa.py`, `services/twofa_service.py`, `token_utils.py`, `custom_tokens.py` |
| `mysite/users` | User profiles, circles, onboarding flows, serializers, background tasks for invites/onboarding | `models/circle.py`, `views/circles.py`, `serializers/circle_invite.py`, `tasks.py` |
| `mysite/keeps` | Media-rich “keep” objects (photos, videos, notes), milestones, social interactions | `models/keep.py`, `models/media.py`, `serializers/keep.py`, `views/keeps.py` |
| `mysite/messaging` | Notifications, in-app messaging, SMS/email templating integration | `services/notification_service.py`, `tasks.py`, `serializers/notification.py` |
| `mysite/emails` | DRY email templating, Celery tasks for sending transactional emails | `templates/`, `tasks.py` |

REST APIs are exposed through Django REST Framework with schema annotations in most views via `drf-spectacular`. Serializers live beside their domain logic (`mysite/users/serializers/`, etc.), and URL routing is split per app then aggregated in `mysite/mysite/urls.py`.

### Authentication Surface
- **Magic Link Login**: `mysite/auth/views.py` issues tokenized login links; tokens stored via `store_token` in `mysite/auth/token_utils.py` leveraging Redis TTL.
- **Google OAuth**: `mysite/auth/views_google_oauth.py` handles OAuth state management with rate limiting; tokens validated through `services/google_oauth_service.py`.
- **Two-Factor Auth**: Time-based OTP flows via `PyOTP` in `services/twofa_service.py`, with recovery codes (`recovery_code_service.py`) and trusted device remember-me (`trusted_device_service.py`).
- **JWT**: DRF SimpleJWT configured in settings, providing short-lived access tokens for API consumption.
- **Rate Limiting**: `django-ratelimit` integrations (env-controlled) protect high-risk endpoints.

### Circles Domain
- **Models**: `Circle`, `CircleMembership`, `CircleInvitation` in `mysite/users/models/circle.py`; ownership is tracked through `UserRole` choices (`mysite/users/models/user.py`).
- **API Endpoints**: `mysite/users/views/circles.py` provides list/create, detail update, invitation create/list/accept endpoints. Invitations currently email-based with Celery email dispatch (`mysite/users/tasks.py`).
- **Serializers**: `CircleInvitationCreateSerializer` and companion serializers under `mysite/users/serializers/`.
- **Technical Debt**: Invitations only support email, no username path; onboarding for invitees without existing accounts is manual; limited rate limiting on invites; minimal audit logging.

### Keeps & Media
- **Keep Model**: `mysite/keeps/models/keep.py` stores metadata, relationships to circles and users.
- **Media Handling**: `mysite/keeps/models/media.py` integrates with MinIO/S3; files managed via storage backends configured in settings.
- **Social Layer**: `mysite/keeps/models/social.py` handles reactions/comments (requires deeper review for concurrency rules).
- **Background Processing**: Media uploads trigger Celery tasks for resizing/transcoding (see `mysite/keeps/tasks.py`).

### Messaging & Notifications
- **Email Templates**: Stored in `mysite/emails/templates/` with Celery tasks in `mysite/emails/tasks.py`.
- **Notification Utils**: `mysite/notification_utils.py` centralizes response envelope creation and message templating.
- **Webhooks/External SMS**: Twilio integration toggled via env (`SMS_PROVIDER`), defaulting to console for development.

### Settings & Environment
- Uses environment-driven configuration for secrets/URLs. Local defaults provided in `.env.example`.
- Postgres configured with optional SQLite fallback (`USE_SQLITE_FALLBACK`) for quick testing.
- Redis handles cache + Celery broker; health checks configured via `django-health-check`.

## Frontend Architecture (React 19 + Vite)
### Tech Stack
- **Build Tooling**: Vite 7 with TypeScript strict mode; `npm run dev` for local hot reload, `npm run build` for production bundling.
- **State/Data**: TanStack Query manages server state; TanStack Router for routing; TanStack Form for controlled forms.
- **UI Layer**: Radix UI primitives styled with Tailwind 4 + `cva`/`tailwind-merge`.
- **Testing**: Vitest + Testing Library (`npm run test`).

### Structure
- `web/src/routes/`: Route definitions mapping to React components in `route-views/` and `features/`.
- `web/src/features/`: Domain-specific bundles (e.g., `auth`, `circles`, `keeps`). Each feature includes API hooks, components, and sometimes local stores.
- `web/src/lib/`: Cross-cutting utilities including API clients (likely wrapping `fetch`/`http` with base URL from `env.ts`).
- `web/src/components/`: Shared UI elements with co-located styles/tests.
- `web/components.json`: Central design tokens consumed by build-time tooling (pending rebuild post-doc reset).

### API Integration
- Base API URL injected via `VITE_API_BASE`. Authentication relies on JWT tokens stored client-side (exact storage strategies to be confirmed in `web/src/features/auth`).
- Circle management screens call Django endpoints for invites/memberships; currently expect email-based flows.
- TODOs for circle invites likely appear under `web/src/features/circles` (requires refinement once backend enhancements land).

## Data Storage & Models
- **Primary Database**: Postgres 16 (Docker) with models defined via Django ORM. Each app maintains its own migrations in `migrations/`.
- **Key Tables**:
  - `users_circle`, `users_circlemembership`, `users_circleinvitation`
  - `users_user` for core user profile and roles
  - `keeps_keep`, `keeps_mediaasset`, `keeps_milestone`
  - `messaging_notification` or similar (verify naming during future ADR writing)
- **Indexes**: Email/circle composite index on `CircleInvitation` for quick lookups; additional indexes TODO per README (performance improvements pending).
- **Object Storage**: MinIO (S3-compatible) for media assets; bucket auto-provisioned via `minio-init` service.

## External Services & Integrations
- **Google OAuth**: Controlled via `GOOGLE_OAUTH_*` env vars in `docker-compose.yml`.
- **Twilio SMS**: Optional; environment toggles to console logging by default.
- **Mailpit**: SMTP sink for local email testing.
- **Flower**: Celery monitoring UI exposed on port 5656.
- **RedisInsight & pgAdmin**: UI tools for Redis/Postgres introspection.
- **MinIO Console**: Available on port 9221 for bucket inspection.

## Local Development Workflow
1. `docker compose up --build` — builds backend image, installs Node dependencies, runs migrations, seeds demo data, starts Django + Celery + frontend + infra.
2. `docker compose exec web python manage.py migrate` — run additional migrations as needed.
3. `docker compose exec web python manage.py test --settings=mysite.test_settings` — backend test suite with in-memory cache/broker.
4. `npm run dev` from `web/` — optional manual frontend dev server (Docker already runs one).

### Environment Files
- `.env.example` — backend environment defaults.
- `web/.env.local.example` (to be created) — recommended pattern for front-end overrides once documentation rebuild progresses.

## Deployment & Operations
- **Containerization**: Dockerfile builds Python runtime with dependencies; Celery workers share image.
- **Production Targets**: Designed for AWS ECS/Fargate + S3 + RDS (see legacy `_docs/architecture.md`; revisit for up-to-date ADR).
- **Static Assets**: React build artifacts served via CDN/static hosting; Django handles API only.
- **Monitoring/Logging**: Flower, RedisInsight, pgAdmin for local; production should integrate Sentry + CloudWatch (needs ADR refresh).

## Testing Reality
- **Backend**: Pytest + Django test runner; tests colocated under each app (`tests/` directories). Coverage of auth/circles needs evaluation (CI not yet configured).
- **Frontend**: Vitest with Testing Library; components expect strict TypeScript.
- **E2E**: No automated E2E currently configured; manual testing via Docker stack.
- **Quality Tools**: Ruff planned per repository guidelines (not yet configured in this repo); Biome handles JS lint/format.

## Technical Debt, Risks, and Gotchas
- **Auth Surface Complexity**: Multiple login methods; invite onboarding must not bypass 2FA/Google flows. Token utilities rely on Redis; ensure TTL alignment for invites vs auth tokens.
- **Invitation Flow Limitations**: Only email-based; no username search or pre-creation handshake. Accept/decline flows triggered via tokens, but UI handling for new-account onboarding is thin.
- **Rate Limiting**: Environment toggles exist but defaults disable limits; production hardening required before launch.
- **Media Scaling**: MinIO buckets seeded automatically but S3 parity not tested; large file handling depends on env vars (`MAX_UPLOAD_SIZE`).
- **Documentation Debt**: `_docs/` now deprecated; ADR process must be rebuilt inside `docs/`. Keep legacy files for historical reference but avoid mixing content.
- **Testing Gaps**: README TODOs mention pagination, indexing, logging, rate limiting—all unfinished and lacking coverage.

## Next Documentation Steps
1. Draft ADR template in `docs/adr-template.md` and migrate critical architectural decisions from legacy `_docs/architecture/adr`.
2. Author circle invite flow ADR once requirements are finalized (post-PRD).
3. Generate service-specific summaries (auth, keeps, messaging) to support AI agents—can leverage `document-project` task per domain.
4. Establish lint/test automation documentation (CI instructions) once tooling decisions are locked.
