# Tinybeans Auth App – Security & Architecture Review

## Scope & Context
- Codebase: `mysite/auth` Django app plus supporting settings in `mysite/settings.py`.
- Focus: authentication flows (signup, login, logout, password lifecycle), JWT handling, two-factor authentication (2FA), and supporting utilities/services.
- Environment assumptions: Django 5.2.x, DRF, SimpleJWT, Redis-backed cache, Celery for async work.

## Architecture Overview
- **Entry points:** Class-based DRF `APIView` endpoints in `auth/views.py` with supplemental 2FA views in `auth/views_2fa.py` and URL routing via `auth/urls.py`.
- **Serialization layer:** DRF serializers in `auth/serializers.py` and `auth/serializers_2fa.py` validate request payloads and orchestrate User model interactions.
- **Domain services:** `auth/services/` encapsulates reusable business logic for OTP generation, trusted device lifecycle, and recovery code export.
- **Data layer:** Models in `auth/models.py` extend the custom `users.User` model with 2FA state, OTPs, recovery codes, trusted devices, and audit logging.
- **Token utilities:** `auth/token_utils.py` centralises JWT creation, partial-token caching for 2FA, and HTTP-only refresh cookie handling.

## Implemented Security Controls
- Uses Django's custom `User` model (`users/models/user.py`) with `create_user` and password hashing via `set_password`.
- Email/password login is fronted by JWT issuance (`auth/token_utils.py:70-107`) with refresh tokens stored in HTTP-only cookies (`set_refresh_cookie`).
- One-time cache-backed tokens (`store_token` / `pop_token`) for email verification and password reset enforce single use and TTLs.
- 2FA stack supports TOTP, email, and SMS, including:
  - Encrypted TOTP secrets via Fernet (`auth/models.py:53-71`).
  - OTP issuance with limited lifetime and attempt counters (`auth/services/twofa_service.py:44-111`).
  - Account lockout and rate-limiting controls on repeated 2FA failures (`auth/models.py:73-102`, `auth/services/twofa_service.py:129-140`).
  - Recovery codes stored as SHA-256 hashes and invalidated on use (`auth/models.py:140-177`).
  - Trusted device “remember me” flow with auto-expiry and audit logging (`auth/services/trusted_device_service.py`).
- Celery task for cleaning expired trusted devices (`auth/tasks.py`).
- CSRF bootstrap endpoint (`auth/views.py:354-360`) supports browser clients in coupling with JWT cookies.

## Alignment With Django & DRF Best Practices
- Relies on DRF serializers for input validation and explicit `APIView` classes, avoiding business logic in serializers.
- Uses service modules to isolate multi-step flows, improving testability (evidenced by `auth/tests/*`).
- Cache-backed token workflow avoids persisting sensitive transient tokens in the database.
- HTTP-only cookies and `samesite` controls lower risk of token theft; defaults tighten automatically when `DEBUG` is false.
- 2FA audit logs and trusted device records provide traceability for security-sensitive events.

## Findings & Recommendations
| Severity | Area | Finding | Recommendation |
| --- | --- | --- | --- |
| **Critical** | Password reset flow | Password reset tokens are returned in the API response to unauthenticated callers (`auth/views.py:264-293`). An attacker can request a reset for any account and immediately take it over. | Remove the token from the response body and only deliver it via trusted channels (email/SMS). Consider logging suspicious requests and rate-limiting the endpoint. |
| **High** | Email verification flow | Signup and verification-resend responses expose verification tokens in plain text (`auth/views.py:45-86`, `auth/views.py:176-204`). Tokens intended for proving email ownership should not leave secure messaging channels. | Stop echoing verification tokens in API responses. If front-end flow needs a token for confirmation, require authenticated retrieval with proof of mailbox access. |
| **High** | Configuration hygiene | Production-secrets are hard-coded (`mysite/settings.py:17-18`, `mysite/settings.py:226-251`) and `DEBUG` defaults to `True` with permissive `ALLOWED_HOSTS`. | Move `SECRET_KEY`, `TWOFA_ENCRYPTION_KEY`, and other credentials into environment variables, default `DEBUG=False`, and populate `ALLOWED_HOSTS` explicitly. Document required settings in deployment guides. |
| **Medium** | Enumeration risk | The email verification resend endpoint discloses whether a username/email exists (`auth/serializers.py:46-70`, `auth/views.py:176-204`), aiding account enumeration. | Return a generic success response regardless of lookup result (similar to the password reset flow) and log mismatches for monitoring. |
| **Medium** | Rate limiting | Login endpoint has commented-out rate limiting decorators (`auth/views.py:93-100`). OTP issuance relies on service-level counters but initial password auth is unrestricted. | Reinstate rate-limiting (per-IP and per-username) using `django-ratelimit` or throttling classes, and ensure operational alerting. |
| **Medium** | 2FA OTP storage | `TwoFactorCode` stores OTP values in clear text (`auth/models.py:105-137`). If database access is compromised, codes can be replayed within their validity window. | Hash OTP codes (e.g., SHA-256 with per-code salt) and compare using constant-time checks. Balance with usability by limiting the verification window. |
| **Medium** | Partial-token IP binding | `verify_partial_token` trusts `X-Forwarded-For` headers without ensuring proxy sanitisation (`auth/token_utils.py:118-158`). | Set `SECURE_PROXY_SSL_HEADER`, restrict trusted proxy IPs, or derive client IP from a vetted header chain. Consider embedding user-agent fingerprinting to make token theft harder. |
| **Low** | Serializer mismatch | `RecoveryCodeSerializer` references a non-existent `code` field (`auth/serializers_2fa.py:42-56`), so serialisation will fail unless a property is added. | Adjust serializer to expose only available fields (e.g., `code_hash` or computed display values) and add tests covering API responses. |
| **Low** | Logging robustness | Multiple service calls swallow exceptions silently (`auth/services/twofa_service.py:97-109`, `auth/services/trusted_device_service.py:68-87`). | Capture and surface delivery failures (email/SMS) through structured logging/metrics to aid incident response. |

## Additional Observations
- Password reset requests correctly avoid identifying whether an account exists when the user is missing, but the response payload must be sanitised (see Critical finding).
- 2FA lockout thresholds and durations are configurable via settings; ensure ops have monitoring to tune these values.
- Trusted device cookies are flagged `httponly` but not `secure` in debug mode. Confirm that production deployments run with HTTPS so Secure cookies are enforced.
- Consider enabling JWT refresh token rotation (`SIMPLE_JWT`) if replay risks are a concern, in tandem with the partial-token safeguards.

## Suggested Next Steps
1. Patch the Critical and High-risk items before releasing the auth service to production; add regression tests for token leakage scenarios.
2. Harden deployment configuration by externalising secrets, tightening debug/host settings, and documenting required environment variables.
3. Re-enable rate limiting and extend telemetry (metrics/logs) around auth endpoints and Celery tasks.
4. Schedule a follow-up review after fixes to validate posture, and integrate checks (lint/tests) that guard against future regressions.

