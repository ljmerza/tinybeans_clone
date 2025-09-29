# Project Primer for Agents

## Overview
- Building a Tinybeans-inspired family photo journal where small “Circles” share memories privately.
- Each circle has guardians (admins) and invited members; child profiles can be upgraded into full accounts once a guardian consents.
- Tech stack highlights: Django 5.2 + DRF, SimpleJWT, Redis cache for short-lived auth tokens, Celery for async work, Mailjet (optional) for outbound email, Dockerized dev environment.

## Key Features Implemented
- Custom `User` and `Circle` models with membership roles, invitations, and child profiles (linked, pending upgrade, unlinked).
- `users` API covers signup/login, email verification, password reset, member invites, guardian consent + child upgrades, and notification preferences.
- Tokens for verification/reset/upgrades live in Redis and are sent via Celery-triggered emails.
- Refresh tokens issued exclusively via HTTP-only cookie + `/api/users/auth/token/refresh/`; access tokens remain short-lived (30 min).
- OpenAPI schema served at `/api/schema`; Swagger UI (`/api/docs`) and Redoc (`/api/redoc`) provide interactive reference.
- `seed_demo_data` (auto-run on container startup) provides superuser + multiple circle scenarios for local smoke tests.

## In-Flight / Next Steps
- Rate limiting: DRF throttles or Redis counters per endpoint (signup/login/password/upgrade).
- Observability: structured logging/metrics around token issuance + email delivery, Flower dashboards in prod.
- Harden email layer: HTML templates, provider abstraction, delivery metrics/alerts.
- Push notifications & mobile experience exploration; eventually multi-tenancy + security audit logging.

## Useful Docs
- `docs/users_app_plan.md` — implementation roadmap, TODOs, future ideas.
- `docs/email_queue_plan.md` — async email design, queue options, Celery decision.
- `DEVELOPMENT.md` — local setup, seeded accounts, testing commands.

## Dev Environment Notes
- `docker compose up --build` (local only) runs DB migrations, seeds demo data, then starts Django; Celery worker/beat/Flower containers provide async email + monitoring.
- Shared env vars (Postgres/Redis/Mailjet) live in the compose `x-common-env` block; override via `.env` or shell exports.
- `.venv` holds deps; inside containers you can run management commands directly (`python manage.py ...`).
- Mailjet keys are optional—without them the console backend logs outbound email content.

Welcome aboard! Dive into the docs above for deeper context before shipping features.
