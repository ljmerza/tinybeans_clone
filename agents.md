# Project Primer for Agents

## Overview
- Building a family-focused photo sharing app inspired by Tinybeans.
- Core concept: **Circle** — a private space where guardians invite relatives/friends to view and contribute memories.
- Tech stack: Django 5.2, Django REST Framework, JWT auth, Redis-backed token store, Docker-based dev environment.

## Key Features Implemented
- Custom `User` model with `Circle` memberships and roles (`admin` vs `member`).
- `main` app exposes a hello-world view; `users` app delivers signup/login, email verification, password reset, invitations, child profile upgrades, and preference APIs.
- Invitation and upgrade tokens stored in Redis; endpoints accept/resend/confirm flows.
- OpenAPI schema exposed at `/api/schema`, Swagger UI at `/api/docs`, ReDoc at `/api/redoc`.

## In-Flight / Next Steps
- Async email pipeline: Celery + Redis for dev (SQS-ready), queuing verification/reset/invite emails.
- Swap inline token responses with real email delivery (SendGrid/Postmark planned).
- Add throttling, observability, and automated tests for new flows.
- Guardian consent, richer child metadata, and admin tooling on the roadmap.

## Useful Docs
- `docs/users_app_plan.md` — implementation roadmap, TODOs, future ideas.
- `docs/email_queue_plan.md` — async email design, queue options, Celery decision.

## Dev Environment Notes
- Docker Compose now runs Django + Redis + PostgreSQL with optional Celery worker/beat/Flower services; everything talks over internal service names (no host port publishing).
- Recent migrations were run locally with `USE_SQLITE_FALLBACK=1`; once Postgres is available re-run `python manage.py migrate` without the flag inside the web container.
- Virtualenv sits at `.venv`; run management commands via `../.venv/bin/python manage.py ...` from `mysite/`.
- Default email backend is console until provider integration lands.

Welcome aboard! Dive into the docs above for deeper context before shipping features.
