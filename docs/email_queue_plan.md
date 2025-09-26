# Async Email Dispatch Plan

## Current Email Touchpoints
- **Verification links**: signup verification, resend verification, child profile upgrades, circle invitations.
- **Password reset**: request + confirm flows.
- **Invitation notifications**: admins invite members, pending invitation reminders, decline notifications.
- Future: guardian consent reminders, digest summaries, new media alerts.

Each trigger currently returns a token in the API response. We need to offload actual email delivery to a background worker so the API response remains fast and reliable.

## Goals for the Async Pipeline
- Fire-and-forget emails from API endpoints; errors are logged/retried without blocking the request.
- Centralize templating + provider integration (SendGrid/Postmark/etc.).
- Allow retries with backoff; track failure metrics.
- Provide local development mocks so contributors can see queued jobs.
- Support production scaling (multiple workers, visibility into in-flight jobs).

## Queue / Worker Options

### Celery + Redis (broker/result backend)
**Pros**
- Mature, battle-tested task queue with rich retry, scheduling, and time limits.
- Large ecosystem, good Django integration (django-celery-beat, flower monitoring).
- Supports multiple brokers (Redis, RabbitMQ, SQS) so migration path exists.

**Cons**
- Heavier setup; requires running Celery workers and beat scheduler.
- Redis broker in dev is fine, but production best practices often push toward RabbitMQ or Redis cluster for reliability.
- Serialization overhead (default JSON/pickle) and configuration complexity.

### RQ (Redis Queue)
**Pros**
- Lightweight, minimal configuration; fits small-to-medium workloads.
- Integrates cleanly with Django via `django-rq`.
- Simple dashboard; uses Redis only.

**Cons**
- Less feature-rich than Celery (no native scheduling, limited retry backoff without extensions).
- Scaling/monitoring story is thinner; fewer knobs for rate limiting.
- Tightly coupled to Redis broker (no pluggable alternative).

### AWS SQS + Worker (custom or Celery w/ SQS broker)
**Pros**
- Fully managed, highly reliable queue with DLQ support and visibility timeouts.
- Horizontally scalable; good fit once the platform grows.
- Integrates with Celery via `celery[redis,sqs]` or custom consumers.

**Cons**
- Requires AWS account, networking; more friction for local development.
- Need an additional worker deployment (EC2/Lambda/containers) to poll SQS.
- Costs and IAM considerations; local mocking adds setup complexity.

### Other Options
- **Huey**: Simple task queue with Redis; lighter than Celery but more features than RQ.
- **Dramatiq**: High-performance queue supporting Redis, RabbitMQ; good alternative with typed messages.
- **Serverless**: Trigger emails directly via AWS SES/Lambda; minimal queue, but vendor lock-in and less control over retries.

## Recommendation
- **Decision**: Adopt **Celery** as the email job runner.
  - Development & staging use Redis as the broker/result backend to keep the stack lightweight.
  - Production can graduate to SQS (or RabbitMQ) by changing Celery broker settings—no task rewrites needed.
  - Ecosystem support (retries, scheduling, monitoring with Flower) lines up with our roadmap.
- Provide a Docker Compose service to run the Celery worker and (optionally) Celery beat for scheduled emails.

## Docker Compose Additions (dev)
```yaml
  celery-worker:
    build: .
    command: celery -A mysite worker -l INFO
    depends_on:
      - redis
    environment:
      REDIS_URL: redis://redis:6379/0
      DJANGO_SETTINGS_MODULE: mysite.settings

  celery-beat:
    build: .
    command: celery -A mysite beat -l INFO
    depends_on:
      - redis
    environment:
      REDIS_URL: redis://redis:6379/0
      DJANGO_SETTINGS_MODULE: mysite.settings
```
- Keep workers optional; developers can run only when testing async flows.
- For email provider mocking, use console backend or MailHog container (future enhancement).

## Task Design
- Define a reusable Celery task `send_email_task(to_email, template_id, context)`.
- API endpoints call `send_email_task.delay(...)` with the required data.
- Ensure tokens/URLs are generated before enqueuing; store metadata for auditing (optional DB table).
- Implement exponential backoff retries for transient failures (network/provider issues).
- Add logging/metrics (Prometheus, Sentry breadcrumbs) to track success/failure rates.

## Deployment Considerations
- Provision dedicated worker dynos/containers separate from web).
- Use environment-specific brokers (Redis in dev, Redis/RabbitMQ/SQS in prod depending on reliability needs).
- Configure secure credentials for email provider via environment variables.
- Add observability: Flower, CloudWatch metrics, or equivalent.

## Next Steps
1. Wire Celery into Django project (settings, `celery.py`, autodiscovery).
2. Add Docker Compose services for workers.
3. Replace inline email responses with Celery task invocations.
4. Build HTML/text templates and integrate with email provider SDK.
5. Add automated tests using Celery’s `CELERY_TASK_ALWAYS_EAGER` mode to verify task invocation.

## Recent Enhancements
- Celery is now part of the Django project with `mysite/mysite/celery.py` and eager-mode toggles in settings for tests.
- Shared `emailing.send_email_task` consolidates verification, password reset, circle invite, and child upgrade emails with retry-friendly Celery configuration.
- Docker Compose bundles optional `celery-worker`, `celery-beat`, and `flower` services to keep async flows observable in development.
- Compose services now communicate via internal hostnames only; ports stay unbound so Flower/web are accessed via `docker compose exec` or reverse proxies when needed.
- Mailjet can be enabled via `MAILJET_API_KEY`/`MAILJET_API_SECRET` environment variables; otherwise the default Django email backend is used for development.

## Enhancement Backlog
- Build production-ready HTML/text templates on top of the Mailjet integration (currently text-only).
- Expose environment-driven deep links (e.g., `FRONTEND_BASE_URL`) so emails link users directly to confirmation flows.
- Ship metrics/logging dashboards (Flower config, Prometheus counters, Sentry breadcrumbs) for delivery success insight.
- Add contract tests around Celery eager mode to guarantee tasks fire from critical endpoints.
