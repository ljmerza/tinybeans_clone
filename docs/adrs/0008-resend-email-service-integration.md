# ADR-0008: Resend Email Service Integration

**Status:** Proposed
**Date:** 2026-09-05
**Author:** Leonardo Merza

## Context

### Background

Tinybeans Circles sends transactional email for every authentication and membership surface: email verification, magic login, password reset, 2FA codes and security alerts, trusted-device notices, circle invitations and reminders, and child-upgrade notices. Production needs a real delivery provider. Resend was chosen as that provider; this ADR records how it plugs into the existing email pipeline.

### Current State

- `mysite/emails/` implements Service → Repository → Model layering (see ADR-008 in `_docs/`). Twelve templates under `mysite/emails/email_templates/*.email.html` render to `RenderedEmail(subject, text_body, html_body)`.
- `EmailTransport.send()` in `mysite/emails/services.py` branches on `settings.MAILJET_ENABLED`. When true it calls `send_via_mailjet()`; otherwise it uses Django's configured `EMAIL_BACKEND` via `EmailMultiAlternatives` / `send_mail`.
- `send_via_mailjet()` in `mysite/emails/mailers.py` is a hand-written `requests.post` client (basic auth, 10 s timeout). It raises `MailerConfigurationError` when disabled and `MailerSendError` on any HTTP ≥ 400 or transport failure.
- `mysite/emails/tasks.py` defines `send_email_task` on the `email` Celery queue with `autoretry_for=(Exception,)`, exponential backoff with jitter, and `max_retries=5`. Every exception, including 4xx validation errors, is retried five times.
- `TwoFactorMailer._enqueue_email()` calls `send_email_task.delay()` and falls back to a synchronous `email_dispatch_service.send_email()` if Celery is unavailable.
- Settings live in `mysite/config/settings/email.py`. `MAILJET_ENABLED = bool(MAILJET_API_KEY and MAILJET_API_SECRET)`; a key present in the environment silently switches the provider on.
- No environment file in the repo (`.env`, `.env.development`, `.env.staging`, `.env.production`, `env/*.env`) sets `MAILJET_*`, and `.env.example` does not document it. The Mailjet path is dead code in practice.
- Development uses Mailpit over SMTP (`docker-compose.yml`: `EMAIL_HOST=mailpit`, port 1025). Tests use the locmem backend (`mysite/config/settings/test.py`).

### Requirements

- Send every existing template through Resend's HTTP API when enabled, with both text and HTML parts.
- Keep the `send_email_task(to_email, template_id, context)` call signature intact (constraint carried over from ADR-008); all current callers in `mysite/auth`, `mysite/circles`, and `mysite/users` continue to work unchanged.
- Development (Mailpit) and test (locmem) flows keep working with no Resend credentials present.
- Celery retries must not produce duplicate emails when Resend accepted a request but the response was lost.
- Requests Resend rejects as invalid must not be retried five times.
- Provider selection must be explicit; a stray API key in an environment must not change behavior on its own.
- Remove the unused Mailjet code path so there is one hosted provider to maintain.

### Constraints

- No new Python dependency is required for the chosen option; `requests` is already pinned in `requirements.txt`.
- Resend enforces a default rate limit of 10 requests per second and daily/monthly sending quotas. Circle invitation reminders run in batches of `CIRCLE_INVITE_REMINDER_BATCH_SIZE=100`.
- Resend `Idempotency-Key` values are unique per request, expire after 24 hours, and are capped at 256 characters.
- Resend requires a verified sending domain (SPF/DKIM DNS records) before `from` addresses on that domain are accepted. Domain setup is a manual, out-of-repo prerequisite.
- Celery is pinned at 5.4.0.

## Options Considered

### Option 1: Direct Resend HTTP client in the existing mailer pattern (chosen)

**Description:** Add `send_via_resend()` to `mysite/emails/mailers.py` using `requests.post` against `https://api.resend.com/emails`, selected by a new explicit `EMAIL_PROVIDER` setting. Delete `send_via_mailjet()` and the `MAILJET_*` settings.

**Pros:**
- No new dependency; `requests` is already pinned.
- Mirrors the existing mailer and its tests (`test_mailers.py` patches `requests.post`); roughly 150 lines including tests.
- Mailpit and locmem are untouched under `EMAIL_PROVIDER=django`.
- Adds an idempotency key and retry classification, fixing a latent double-send / over-retry problem in the current transport.

**Cons:**
- Hand-maintained client; Resend API changes are ours to track.
- No webhook or bounce tracking in this ADR.
- One provider branch remains in `EmailTransport.send()`.

### Option 2: Official `resend` Python SDK behind a provider protocol

**Description:** Add the `resend` PyPI package and refactor `EmailTransport` into an `EmailProvider` protocol with Resend, Mailjet, and Django-backend implementations chosen by a factory.

**Pros:**
- Typed SDK exceptions (`RateLimitError`, `ValidationError`, `InvalidApiKeyError`) and first-class `idempotency_key` option.
- Clean seam for a future third provider; each provider unit-testable in isolation.

**Cons:**
- New dependency; the SDK holds the API key in module-global state, which complicates test isolation.
- Refactors `EmailTransport`, moves `send_via_mailjet`, and touches `test_services.py` and `test_mailers.py`.
- More files and indirection than a single-provider application needs.
- The SDK's own dependency pins were not verified against `requirements.txt`.

**Why not:** The transport already is the abstraction seam. A protocol refactor adds structure for a second provider that does not exist.

### Option 3: django-anymail with the Resend ESP backend

**Description:** Install `django-anymail` (plus `svix` for webhook signatures), set `EMAIL_BACKEND=anymail.backends.resend.EmailBackend`, collapse `EmailTransport.send()` to the Django-backend path only, and optionally mount `anymail.urls` for delivery-event webhooks.

**Pros:**
- Provider switch becomes an environment variable; Mailpit and locmem still work because they are Django backends.
- Removes provider code from the app instead of adding it.
- Bounce, complaint, and delivered webhooks with signature validation out of the box.

**Cons:**
- Two new dependencies and another abstraction over the Resend API.
- `AnymailAPIError` on 4xx still hits Celery's retry-on-any-exception, so the over-retry problem stays unless the task is also changed.
- Not verified whether Anymail exposes Resend's `Idempotency-Key` header; `esp_extra` merges into the JSON body, not request headers.
- Deletes the existing Mailjet code and tests, same as Option 1, but replaces a house pattern with a library.

**Why not:** Webhook tracking is the main gain, and it is not a requirement today. The idempotency gap is a real regression risk for retried Celery tasks.

### Option 4: Resend SMTP relay

**Description:** Configuration only. Point Django's SMTP backend at `smtp.resend.com` with username `resend` and the API key as password, and wire `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` from the environment (they are not currently read in `email.py`).

**Pros:**
- Two lines of settings, no mailer code, no new dependencies.
- Same code path already used for Mailpit.

**Cons:**
- New SMTP connection per message; `_send_via_django_backend` does not reuse connections.
- No message IDs, tags, idempotency, or typed errors; only `smtplib` exceptions.
- No webhooks; delivery status only visible in the Resend dashboard.
- Resend documents the HTTP API as the primary integration path.
- Leaves the dead Mailjet code in place.

**Why not:** Acceptable as a stopgap, weak as the long-term decision. Loses idempotency and observability for no code saving that matters.

## Decision

**Chosen Option:** Option 1, direct Resend HTTP client in the existing mailer pattern, with the Mailjet path removed.

**Rationale:**
- Zero new dependencies and the smallest diff that meets every requirement.
- Follows the pattern the codebase already uses and tests, so the change is reviewable against `send_via_mailjet` line by line.
- The idempotency key and retry classification are cheap to add in a hand-written client and fix real defects in the current transport. Options 3 and 4 could not guarantee idempotency.
- Mailjet is unused in every environment file in the repo. Removing it leaves one hosted provider and one branch.

### Design

**Settings** (`mysite/config/settings/email.py`):

| Setting | Env var | Default | Notes |
|---------|---------|---------|-------|
| `EMAIL_PROVIDER` | `EMAIL_PROVIDER` | `django` | Allowed: `resend`, `django`. Any other value raises `ImproperlyConfigured` at import. |
| `RESEND_API_KEY` | `RESEND_API_KEY` | `''` | Required when `EMAIL_PROVIDER=resend`; otherwise `ImproperlyConfigured` at import. |
| `RESEND_API_URL` | `RESEND_API_URL` | `https://api.resend.com/emails` | Overridable for tests / mocks. |
| `RESEND_FROM_EMAIL` | `RESEND_FROM_EMAIL` | `DEFAULT_FROM_EMAIL` | Must be on a verified Resend domain. |
| `RESEND_FROM_NAME` | `RESEND_FROM_NAME` | `Tinybeans Circles` | Rendered as `Name <email>` in `from`. |
| `RESEND_TIMEOUT_SECONDS` | `RESEND_TIMEOUT_SECONDS` | `10` | Passed to `requests.post(timeout=)`. |

All `MAILJET_*` settings are removed. `mysite/config/settings/test.py` sets `EMAIL_PROVIDER = 'django'`.

**Mailer** (`mysite/emails/mailers.py`):

- `send_via_resend(*, to_email, subject, text_body, html_body, template_id, idempotency_key=None)`.
- Request: `POST RESEND_API_URL`, headers `Authorization: Bearer <key>`, `Idempotency-Key: <idempotency_key>` when provided. Body: `from`, `to: [to_email]`, `subject`, `text`, `html` (only when present), `tags: [{"name": "template", "value": <sanitized template_id>}]`. Tag values are restricted to ASCII letters, digits, underscore, and dash; the mailer sanitizes `template_id` before sending.
- Error mapping:
  - `requests.RequestException` (timeout, connection) → `MailerSendError` (retryable).
  - HTTP 429 and any 5xx → `MailerSendError` (retryable).
  - Any other 4xx → new `MailerPermanentError(RuntimeError)` (terminal). The Resend error `name` and `message` from the response body are included in the exception message.
- Logs the Resend `id` from a 2xx response at `INFO`. Never logs request headers or the API key.
- `MailerConfigurationError` is removed; provider misconfiguration is caught at settings import instead.

**Transport / service** (`mysite/emails/services.py`):

- `EmailTransport.send(*, to_email, template_id, content, idempotency_key=None)` branches on `settings.EMAIL_PROVIDER`: `resend` → `send_via_resend`, else `_send_via_django_backend`. The Mailjet branch and the configuration-error fallback are removed.
- `EmailDispatchService.send_email(*, to_email, template_id, context, idempotency_key=None)` passes the key through. The synchronous fallback in `TwoFactorMailer._enqueue_email` passes none (single attempt, nothing to deduplicate).

**Task** (`mysite/emails/tasks.py`):

- `send_email_task` passes `idempotency_key=self.request.id`. The Celery task id is stable across retries of the same task, so every retry carries the same key and Resend deduplicates within its 24-hour window. Five retries with exponential backoff complete well inside that window.
- `dont_autoretry_for=(MailerPermanentError,)` is added to the decorator. The task catches `MailerPermanentError`, logs at `ERROR` with `template_id` and recipient, and returns without raising. Call signature is unchanged.

**Configuration surface:** `.env.example`, `docker-compose.yml` (shared environment block, `EMAIL_PROVIDER` defaulting to `django`), and the DEVELOPMENT.md environment table gain the new variables.

## Acceptance Criteria

- [ ] **AC-1**: Given `EMAIL_PROVIDER=resend` and `RESEND_API_KEY` set, when `email_dispatch_service.send_email()` is called with a registered template, then exactly one POST is made to `RESEND_API_URL` with header `Authorization: Bearer <key>` and a JSON body whose `from` is `"<RESEND_FROM_NAME> <<RESEND_FROM_EMAIL>>"`, `to` is `[to_email]`, `subject`/`text`/`html` match the rendered template, and `tags` contains `{"name": "template", "value": <sanitized template_id>}`.
- [ ] **AC-2**: Given `EMAIL_PROVIDER=django` (the default), when `send_email()` is called, then no HTTP request is made and the message is delivered through Django's configured `EMAIL_BACKEND` (locmem outbox in tests) with the same subject, text body, and HTML alternative as today.
- [ ] **AC-3**: Given `EMAIL_PROVIDER=resend` with an empty `RESEND_API_KEY`, or `EMAIL_PROVIDER` set to a value outside `{resend, django}`, when the settings module is imported, then `django.core.exceptions.ImproperlyConfigured` is raised.
- [ ] **AC-4**: Given Resend responds with HTTP 429 or any 5xx, or `requests.post` raises `requests.RequestException`, when `send_via_resend()` is called, then `MailerSendError` is raised, and when the same failure occurs inside `send_email_task` the task schedules a retry.
- [ ] **AC-5**: Given Resend responds with a 4xx other than 429 (for example 422 validation or 401 invalid key), when `send_via_resend()` is called, then `MailerPermanentError` is raised, and when the same failure occurs inside `send_email_task` the task logs at `ERROR`, does not raise, and does not retry.
- [ ] **AC-6**: Given `send_email_task` executes, when it calls Resend on the first attempt and on every retry, then each POST carries an `Idempotency-Key` header equal to the task's Celery id, identical across all attempts of that task.
- [ ] **AC-7**: Given the Mailjet removal, when `grep -rn MAILJET mysite/` and `grep -rn "send_via_mailjet\|MailerConfigurationError" mysite/` are run, then both return nothing, and the backend test suite passes with no failures beyond the documented pre-existing set.
- [ ] **AC-8**: Given a fresh checkout, when `.env.example`, `docker-compose.yml`, and DEVELOPMENT.md are read, then `EMAIL_PROVIDER`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `RESEND_FROM_NAME` are documented, and `docker compose config` shows `EMAIL_PROVIDER=django` for the web and celery services when the variable is unset.

## Consequences

### Positive
- Production email goes through a maintained hosted provider with message IDs visible in the Resend dashboard.
- Retried Celery tasks can no longer send the same email twice.
- Invalid requests fail once with a clear log line instead of five silent retries.
- Provider selection is explicit and validated at startup.
- One hosted provider to maintain; roughly 80 lines of unused Mailjet code and its tests are gone.

### Negative
- Re-adding Mailjet or any other provider now requires code, not just credentials.
- The Resend client is hand-written; API changes must be tracked manually.
- Delivery-status webhooks (bounces, complaints) are out of scope. Bounce handling stays manual until a follow-up ADR.
- `MailerPermanentError` classification means a transient 4xx (for example 401 during API-key rotation) drops the email rather than retrying it.

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Invitation reminder batches (100 per run) exceed Resend's 10 req/s default limit and hit 429 | Low | Low | 429 maps to `MailerSendError`, so backoff retries absorb it. If it recurs, add `rate_limit='8/s'` to `send_email_task`. |
| Sending domain not verified in Resend, so every send returns a 4xx and is dropped | Medium at first deploy | High | Documented prerequisite in the implementation plan. Verify the domain and send one test email before switching `EMAIL_PROVIDER` in production. Staging may use Resend's `onboarding@resend.dev` sender, which only delivers to the account owner's address. |
| API key rotated while workers are running; 401 is classified permanent and emails are lost | Low | Medium | Every send fails, so the `ERROR` log volume makes it visible immediately. Rotate by deploying the new key before revoking the old one. |
| API key appears in logs or tracebacks | Low | High | Mailer logs only status code and Resend's error `name`/`message`; `Authorization` header is never logged. |
| Free-tier daily/monthly quota exhausted | Low | Medium | Quota exhaustion returns a retryable error class in Resend's API; retries with backoff cover short outages. Check current quotas at resend.com/pricing before relying on the free tier for reminder batches. |

## Implementation Plan

- [ ] Phase 0 (manual, out of repo): add the sending domain in the Resend dashboard, publish SPF/DKIM DNS records, confirm verification, create an API key with send-only permission.
- [ ] Phase 1, settings: add `EMAIL_PROVIDER` and `RESEND_*` to `mysite/config/settings/email.py` with import-time validation; remove `MAILJET_*`; update `mysite/config/settings/test.py`; add variables to `.env.example`, the shared environment block in `docker-compose.yml`, and the DEVELOPMENT.md table.
- [ ] Phase 2, mailer: implement `send_via_resend()` and `MailerPermanentError` in `mysite/emails/mailers.py`; delete `send_via_mailjet`, `_build_payload`, and `MailerConfigurationError`; replace `MailjetMailerTests` in `mysite/emails/tests/test_mailers.py` with `ResendMailerTests` covering AC-1, AC-4, AC-5, AC-6 at the mailer level.
- [ ] Phase 3, plumbing: thread `idempotency_key` through `EmailTransport.send()` and `EmailDispatchService.send_email()`; branch on `EMAIL_PROVIDER`; update `send_email_task` with `self.request.id` and `dont_autoretry_for`; update `test_services.py`, `test_tasks.py`, and `mysite/users/tests/test_async_email.py` (the only test outside the emails app that references `MAILJET_*`).
- [ ] Phase 4, verification: run the backend suite; confirm AC-7 greps are empty; set `EMAIL_PROVIDER=resend` in staging and send one verification email end to end; confirm the message id appears in the Resend dashboard.

## Related ADRs

- [ADR 0001](./0001-circle-invite-flow.md) - Circle invitation and reminder emails are the highest-volume consumers of this transport.
- ADR-008 (`_docs/architecture/adr/ADR-008-EMAIL-TEMPLATE-SYSTEM.md`) - Defines the template rendering that produces the subject/text/html this transport sends, and the `send_email_task` contract this ADR preserves.
- ADR-003 (`_docs/architecture/adr/ADR-003-TWO-FACTOR-AUTHENTICATION.md`) - 2FA code and security-alert emails are sent through `TwoFactorMailer`, which uses this pipeline.

## References

- Resend send-email API: https://resend.com/docs/api-reference/emails/send-email
- Resend error reference (quota, rate limit, validation): https://resend.com/docs/api-reference/errors
- Resend account quotas and rate limits: https://resend.com/docs/knowledge-base/account-quotas-and-limits
- django-anymail Resend backend (rejected Option 3): https://anymail.dev/en/stable/esps/resend/
- Celery automatic retry and `dont_autoretry_for`: https://docs.celeryq.dev/en/stable/userguide/tasks.html#automatic-retry-for-known-exceptions
