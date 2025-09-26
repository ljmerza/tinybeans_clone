# Users App Follow-Up TODOs

## Immediate Next Steps
- Enforce per-endpoint throttling (DRF throttles or Redis counters) for signup, login, password-reset, and child-upgrade flows.
- Add comprehensive automated tests (serializers, viewsets, permissions, Redis token expiration) and integrate them into CI.
- Add proper error/result logging and metrics (e.g., Prometheus counters for token issuances and verification success rates).
- Add task-queue observability (Flower dashboard in dev, CloudWatch metrics in prod).
- Document token refresh cookie flow in public API docs / developer portal.

## Recently Completed
- Centralized email delivery in the standalone `emailing` app with Mailjet support and template registry.
- Moved long-lived refresh tokens into HTTP-only cookies plus dedicated refresh endpoint.
- Added richer child profile metadata, guardian consent logging, and admin tooling for upgrades.
- Introduced `seed_demo_data` command and auto-run during `docker compose up` for consistent local fixtures.
- Updated OpenAPI descriptions for user endpoints (notification prefs, child upgrades, invitation flows).

## Longer-Term Ideas
- Expand Celery-backed background processing to cover digest emails, push notifications, and other asynchronous workloads.
- Add device push notification support with per-user channel preferences.
- Implement audit logging for critical security events (login, password changes, upgrades) stored in an append-only log.
- Introduce analytics endpoints/dashboard for circle engagement (uploads per week, active members, viewed albums).
- Evaluate multi-tenancy concerns (per-organization domains), especially if circles eventually belong to larger communities.

## Async Email Notes
- Celery wiring lives in `mysite/mysite/celery.py` with eager-mode toggles in settings for tests.
- Dev/staging: Redis broker; production: swap to SQS/RabbitMQ without rewriting tasks.
- `emailing.send_email_task` handles verification, password reset, circle invitations, and child upgrades with Celery retries.
- Docker Compose includes `celery-worker`, `celery-beat`, and `flower` services so developers can observe tasks locally.
- Mailjet credentials are optional; the command falls back to Django's console backend for developers.
- Next enhancements: add HTML templates, tracking metadata, and structured metrics (see `docs/email_queue_plan.md`).
