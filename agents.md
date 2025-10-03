# Project Primer for Agents

## Overview
- Privacy-first Tinybeans-inspired journal: Django 5.2 + DRF powers the API, while a Vite/TanStack Router SPA ships the member experience.
- Authentication now spans username/password, passwordless magic links, Google OAuth 2.0 (initiate/callback/link/unlink), and rich 2FA flows (TOTP, SMS, email) with trusted devices.
- Redis backs token storage and rate limiting; Celery + Flower handle async work; Mailjet/Mailpit and an SMS provider abstraction (Twilio-ready) deliver notifications.
- Keeps service processes photo/video uploads asynchronously via MinIO/S3-compatible storage, thumbnail generation, and Celery-driven status tracking.
- Docker compose stack includes auxiliary dashboards (Dashy, pgAdmin, RedisInsight, MinIO) so agents can inspect every subsystem quickly.

## Key Features Implemented
- **Accounts & Auth**: Custom `User`/`Circle` domain, email verification, password reset, invitations, guardian consent, JWT refresh via HTTP-only cookies, and Redis-issued tokens.
- **Advanced Login Options**: Google OAuth endpoints with PKCE + state storage, passwordless magic links, and full 2FA suite (setup/verify/disable, recovery codes, trusted devices, audit log, rate limits, lockouts).
- **Media & Keeps**: `keeps` app exposes CRUD + async upload pipeline, pluggable storage backends (local/MinIO/S3), multi-size thumbnails, Celery tasks, and presigned access URLs.
- **Messaging & Notifications**: Email dispatcher with reusable templates, SMS provider abstraction (console/Twilio) for OTP delivery, and Celery beat cleanup routines.
- **Frontend SPA**: React + TanStack Query/Router with CSRF bootstrap, login/signup/magic link flows, Google OAuth button + callback route, and comprehensive 2FA management screens.
- **Documentation & Tooling**: Rich docs set (ADRs, feature briefs, security reports, epic summaries), Spectacular-generated OpenAPI (`/api/docs`, `/api/redoc`), seeded demo data, and automated test settings.

## In-Flight / Next Steps
- Ship Google account linking UI inside the account settings area (Epic 4 story 4.6 still open).
- Finish productizing the Photo Calendar React library per `docs/features/photo-calendar/MVP_IMPLEMENTATION_PLAN.md`.
- Define audit log retention/rotation strategy for 2FA + OAuth events (last pending security enhancement).
- Extend keeps to cover richer search/favorites/pagination per `README.md` backlog.
- Fill remaining observability gaps: structured auth event logging, email/SMS delivery metrics, and rate-limit dashboards.

## Useful Docs
- `docs/README.md` — global documentation index and navigation map.
- `docs/features/2fa/2FA_DOCUMENTATION_INDEX.md` — end-to-end 2FA architecture, services, and troubleshooting.
- `docs/features/oauth/GOOGLE_OAUTH_IMPLEMENTATION.md` — Google OAuth flow details, error codes, and security notes.
- `docs/features/media-storage/MEDIA_STORAGE_IMPLEMENTATION_SUMMARY.md` — async media pipeline and storage backends.
- `docs/guides/planning/TINYBEANS_KEEPS_COMPLETE_SUMMARY.md` — keeps domain overview and API surface.
- `DEVELOPMENT.md` — local setup, seeded accounts, OAuth configuration, and testing commands.

## Dev Environment Notes
- Run `docker compose up --build` to launch Django API, Celery worker/beat, Flower, React dev server, MinIO, Mailpit, pgAdmin, RedisInsight, and the Dashy service catalog.
- `.env` controls shared settings (Postgres, Redis, Mailjet, OAuth, 2FA keys); override per-service variables as needed.
- `python manage.py seed_demo_data` reruns the demo fixture—handy after schema changes.
- Tests use `mysite.test_settings` for in-memory brokers/cache, so `python manage.py test --settings=mysite.test_settings` stays hermetic.
- Dashy (`dashy-config.yml`) lists ports, credentials, and quick actions; tweak the config and restart `dashy` to customize.

Welcome aboard! Use this primer plus the docs above to orient quickly before taking on new tickets.
