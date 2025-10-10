# Django Backend Improvement Plan (Django 5.2)

Prepared: 2025‑02‑14  
Scope: `mysite/` Django project (apps: `auth`, `users`, `keeps`, `messaging`, `emails`)

## Objectives
- Align the backend with the Django 5.2 hardened deployment checklist, OWASP ASVS L2, and current DRF guidance.
- Close gaps in auth flows, media handling, and configuration before production launch.
- Provide an ordered backlog the team can execute iteratively (P0 = release blocker, P1 = high priority, P2 = mid‑term hardening).

## Priority Findings

| Priority | Area | Observation | Recommendation | References | Status |
| --- | --- | --- | --- | --- | --- |
| **P0** | Circle invitations | Invitation API echoes the single-use invite token back to the caller, making phishing or privilege escalation trivial if an admin account is compromised. | Deliver invitation tokens exclusively via email. Remove `data['token'] = token` from the response payload. | `mysite/users/views/circles.py:150-177` | [x] Done – token removed from API response |
| **P0** | Passwordless login | Magic-login tokens are stored and queried in clear text, so database access allows session hijacking. | Persist a salted hash (e.g., SHA256) and compare in constant time; store the raw token only in email templates. | `mysite/auth/models.py:320-352`, `mysite/auth/views.py:452-560` | [x] Done – hashed lookup in place |
| **P0** | Production security headers | Core HTTPS protections (`SECURE_SSL_REDIRECT`, HSTS, secure cookies, referrer policy, CSRF trusted origins) are missing. | Add the standard Django 5 deployment hardening block gated by `DEBUG`. Document required env vars. | `mysite/mysite/config/settings/base.py` | [x] Done – security headers gated by `DJANGO_SECURE_*` env vars |
| **P1** | Media upload pipeline | Validation task lacks video probing, antivirus scanning, and image bomb protections; thumbnails are written twice and ignore SSE/CSP concerns. | Integrate ffprobe/mediainfo checks, ClamAV (or SaaS AV), enforce `Image.MAX_IMAGE_PIXELS`, and refactor thumbnail writes to a single `storage.save` call with deterministic keys + server-side encryption headers. | `mysite/keeps/views/upload_views.py:55-155`, `mysite/keeps/tasks.py:91-175`, `mysite/keeps/storage.py:69-180` | [ ] Pending |
| **P1** | API-wide defaults | REST framework uses `AllowAny` by default and lacks throttles outside auth endpoints. | Set `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']` (override per anon endpoints) and add `UserRateThrottle`/`AnonRateThrottle` plus settings-driven limits. | `mysite/mysite/config/settings/base.py` | [ ] Pending |
| **P1** | Observability | No structured logging, request tracing, or health-check endpoints exist, leaving ops blind to auth/media incidents. | Introduce JSON logging (structlog or DRF formatter), request IDs, Celery task metrics, and `/health/` endpoints (readiness & liveness). | project-wide | [ ] Pending |
| **P2** | Trusted device hygiene | Device IDs are long-lived with no periodic rotation or signature, and cookies are not bound to user agents/IP. | Rotate trusted-device cookies periodically, bind to hashed UA/IP, and sign cookies (e.g., using Django signing) to prevent client tampering. | `mysite/auth/services/trusted_device_service.py:10-159`, `mysite/auth/views_2fa.py:720-820` | [x] Done – signed cookies w/ UA & IP binding plus rotation |
| **P2** | Configuration ergonomics | Single monolithic `settings.py` mixes dev/prod concerns, making misconfiguration likely. | Adopt `config/settings/{base,local,staging,production}.py` or pydantic settings, add `.env` schema, and ensure secrets never default in code. | `mysite/mysite/config/settings/*` | [x] Done – settings split with env profiles + env reference |

## Configuration & Platform Hardening (P0/P1)
- [x] **HTTPS & proxy awareness:** Add the full security stanza (`SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `SECURE_HSTS_SECONDS`, `SECURE_REFERRER_POLICY`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_CROSS_ORIGIN_OPENER_POLICY`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE='Lax'`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_SAMESITE='Strict'`, `CSRF_TRUSTED_ORIGINS` from env). Reference Django deployment checklist. (Implemented behind `DJANGO_SECURE_*`, `DJANGO_SESSION_*`, `DJANGO_CSRF_*`, and `DJANGO_CSRF_TRUSTED_ORIGINS` env vars.)
- [ ] **CORS / CSRF separation:** Move CORS allow-lists to environment variables (both dev and prod) and ensure `CORS_ALLOW_CREDENTIALS` only when the origin list is explicit.
- [ ] **Database & cache:** Configure `CONN_MAX_AGE`, SSL (`OPTIONS={'sslmode': 'require'}`) for Postgres, and add health checks for Redis. Consider `django-health-check` for operational readiness.
- [x] **Settings layout:** Split settings into `mysite/mysite/config/settings/{base,local,staging,production,test}.py` with a compatibility shim and documented env vars (`docs/guides/security/env_reference.md`).
- [ ] **STORAGES API:** Switch from custom loader to Django 5 `STORAGES = {'default': ..., 'staticfiles': ...}` so S3/MinIO can leverage official backends when moving to AWS.
- [ ] **SimpleJWT:** Enable refresh rotation (`ROTATE_REFRESH_TOKENS=True`) and store blacklisted tokens in Redis to mitigate replay. Expose rotation window via settings.

## Authentication & Authorization
1. **Invite token leakage (P0):** Status [x] – response payload now omits invite tokens; follow-up tests still recommended.
2. **Magic login hashing (P0):** Status [x] – tokens persisted via `token_hash`; ensure test suite covers lookup and reuse prevention.
3. **Rate limiting coverage (P1):** Status [ ] – password reset and verification flows still need explicit throttles.
4. **Trusted-device improvements (P2):** Status [x] – cookies now signed and rotated with UA/IP hash binding (`auth/services/trusted_device_service.py`).
    - Added signed cookies (`django.core.signing.TimestampSigner`) and per-request fingerprint validation.
    - Rotation window driven via `TWOFA_TRUSTED_DEVICE_ROTATION_DAYS` with automatic reissue.
    - Trusted-device listings remain unchanged; management API unaffected.
5. **2FA OTP storage (stretch):** Status [x] – OTP codes persisted as HMAC-SHA256 hashes with previews only (`auth/models.py`, `auth/services/twofa_service.py`).
6. **Partial token binding:** Status [x] – partial tokens include user-agent hashes; verification checks IP + UA fingerprints (`auth/token_utils.py`).

## Media & File Handling
- [ ] **Secure temp storage (P1):** Replace `tempfile.gettempdir()` with `NamedTemporaryFile` inside a dedicated `MEDIA_UPLOAD_TMP` directory owned by the app. Guard with `os.open(..., 0o600)` to prevent other containers from reading uploads. (`mysite/keeps/views/upload_views.py:112-121`)
- [ ] **Content validation pipeline (P1):**
  - **Images:** Set `Image.MAX_IMAGE_PIXELS` to cap decompression bombs, re-open images after `.verify()` to avoid truncated file issues, and block unsupported formats.
  - **Videos:** Run `ffprobe`/`mediainfo` to check codecs, duration, and stream count before accepting. Enforce whitelist of containers/codecs.
  - **Antivirus:** Integrate ClamAV (via `clamd`) or a managed malware scanning service and fail the upload until clean.
  - **Content moderation (optional):** Provide hook for future Nudity/CSAM detection before publishing.
- [ ] **Storage backend (P1):**
  - Reuse a singleton MinIO/S3 client (`lru_cache` around `get_storage_backend`) to reduce connection churn.
  - Add server-side encryption (`sse`, `ssec`) and object retention flags for compliance.
  - Use deterministic derivative keys (`f"{base_key}_thumb.jpg"`) and a single `storage.save` call; keep the returned key instead of issuing duplicate writes (`mysite/keeps/tasks.py:126-160`).
  - Add signed URL expirations aligned with product requirements and restrict MIME types when serving downloads.
- [ ] **Async task resilience (P1/P2):** Wrap thumbnail generation in a try/finally block that always closes images, and capture metrics (duration, success/failure counts) via Celery signals.

## Observability & Operational Readiness
- [ ] **Structured logging (P1):** Configure Django/DRF logging to emit JSON with request IDs, user IDs, and correlation IDs. Mirror the config in Celery workers.
- [ ] **Tracing & metrics:** Instrument key flows (login, upload, Celery tasks) with OpenTelemetry spans and Prometheus counters/histograms. Deploy Flower behind authentication.
- [ ] **Health endpoints (P1):** Add `/health/live` and `/health/ready` views that check database, cache, Celery queue depth, and MinIO connectivity. Use Django’s `check` framework or `django-health-check`.
- [ ] **Alerting:** Emit warnings when rate limits trip, 2FA lockouts occur, or storage errors happen. Hook into Sentry or AWS SNS for paging.

## Testing & Governance
- [ ] Extend test coverage to include:
  - Invite flow regression (token not leaked).
  - Magic-login hash validation, reuse prevention, and rate-limited failure paths.
  - Media pipeline negative tests (oversized images, malformed videos, quarantined malware).
- [ ] Add `pytest` markers for smoke tests that run in CI (`pytest --maxfail=1 --disable-warnings -m "not slow"`).
- [ ] Update QA checklist in `docs/guides/security/SECURITY_AUDIT.md` to reflect new controls and add verification steps for each config toggle.
- [ ] Introduce bandit/pylint checks focusing on security anti-patterns (`bandit -r mysite` in CI).

## Suggested Execution Order
1. **Config baseline:** Implement secure settings split + HTTPS headers, add REST framework defaults, update documentation (.env template).
2. **Auth fixes:** Patch invite and magic-login flows, deploy hashed tokens, and expand rate limiting; release once regression suite passes.
3. **Media pipeline:** Land temp-file hardening, validation enhancements, and MinIO refactor; shadow deploy with feature flag if needed.
4. **Observability:** Roll out structured logging, health endpoints, and tracing in staging, then production.
5. **Trusted-device & OTP hashing:** Schedule as a follow-up sprint once visibility is in place to monitor any UX regressions.

Keeping this backlog visible (e.g., mirrored into Linear/Jira) will ensure the Django backend meets modern security expectations before customer data is onboarded.
