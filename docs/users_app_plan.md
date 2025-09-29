# Users App Follow-Up TODOs

## Immediate Next Steps
- Enforce per-endpoint throttling (DRF throttles or Redis counters) for signup, login, password-reset, and child-upgrade flows.
- Add proper error/result logging and metrics (e.g., Prometheus counters for token issuances and verification success rates).
- Add task-queue observability (Flower dashboard in dev, CloudWatch metrics in prod).
- Document token refresh cookie flow in public API docs / developer portal.

## Longer-Term Ideas
- Expand Celery-backed background processing to cover digest emails, push notifications, and other asynchronous workloads.
- Add device push notification support with per-user channel preferences.
- Implement audit logging for critical security events (login, password changes, upgrades) stored in an append-only log.
- Introduce analytics endpoints/dashboard for circle engagement (uploads per week, active members, viewed albums).
- Evaluate multi-tenancy concerns (per-organization domains), especially if circles eventually belong to larger communities.
