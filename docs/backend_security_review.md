# Backend Security & Architecture Review

_Date: 2025-02-14_

## Summary
- Resolved: OAuth callback no longer returns refresh tokens in the JSON payload, keeping refresh secrets HttpOnly-only.
- Resolved: Client IP handling now honours trusted proxy settings and resists spoofed `X-Forwarded-For` headers.
- Resolved: Storage settings enforce non-default credentials and HTTPS in staging/production unless explicitly opted out.
- Resolved: Signup endpoints now carry environment-aware rate limits to deter scripted abuse.
- Resolved: PKCE state rows only persist hashed verifiers, with plaintext stored transiently in cache.

## Findings

### High Priority
- **Keep refresh tokens HttpOnly-only**  
  - Reference: `mysite/auth/views/google_oauth/callback.py:108`  
  - Risk: The callback response embeds the refresh token while also setting the HttpOnly cookie. Any XSS in the SPA (or a malicious browser extension) could now extract the long-lived refresh token and mint new sessions, defeating the defense-in-depth design the other auth flows use.  
  - Recommendation: Return only the access token (or omit the `tokens` payload entirely) and rely on the existing `set_refresh_cookie` call. Update the OpenAPI serializer accordingly so clients do not expect the refresh token in JSON.  
  - Status: Resolved — the callback response now omits refresh tokens and serializers accept access-only payloads.

- **Harden client IP resolution for rate limiting & device trust**  
  - References: `mysite/auth/token_utils.py:164`, `mysite/auth/views/google_oauth/helpers.py:18`  
  - Risk: Both helpers trust the first value of `X-Forwarded-For` without verifying that the request actually came through a trusted proxy. Attackers can spoof this header to reset rate-limit counters, bypass 2FA lockouts, or mint “trusted device” cookies bound to fake IPs.  
  - Recommendation: Centralize IP extraction with a utility that honours Django’s `SECURE_PROXY_SSL_HEADER`/`USE_X_FORWARDED_HOST` configuration and optionally enforces a `TRUSTED_PROXIES` allowlist. Fall back to `REMOTE_ADDR` when headers are missing or untrusted, and let development retain the current permissive behaviour via settings toggles so local testing stays simple. Update all callers (rate limiting, device trust, audit logging) to use the hardened helper.  
  - Status: Resolved — a shared IP resolver now enforces environment-aware proxy trust with new `TRUST_FORWARDED_FOR`/`TRUSTED_PROXY_IPS` settings.

### Medium Priority
- **Enforce secure storage configuration for MinIO/S3**  
  - Reference: `mysite/config/settings/storage.py:16`  
  - Risk: When `DEBUG=False`, continuing to accept the default `minioadmin` credentials or plain HTTP endpoint would leak media and credentials if operators forget to override environment variables. There is no guardrail to catch that misconfiguration.  
  - Recommendation: During production/staging boot, raise `ImproperlyConfigured` if the access or secret key still equals the default or if the endpoint is HTTP with `MINIO_USE_SSL=False`, while keeping relaxed defaults behind an environment check for `DEBUG` or `ENVIRONMENT == 'local'`. Consider defaulting to HTTPS and requiring explicit opt-out for local development.  
  - Status: Resolved — non-local environments now assert secure credentials/HTTPS unless explicitly opted out via `DJANGO_ALLOW_INSECURE_MINIO`.

- **Rate limit signup to curb automated abuse**  
  - Reference: `mysite/auth/views/account.py:54`  
  - Risk: Unlike login, password reset, and magic-link flows, account creation gets no `django-ratelimit` protection. Attackers can script mass signups to farm demo data, enumerate invitation flows, or trigger large volumes of mail.  
  - Recommendation: Add IP + identifier throttles (e.g., `@ratelimit(key='ip', rate='5/m', block=True)` and a secondary email-based key) and reuse the existing `rate_limit_response` utilities for consistency. Provide an environment toggle (similar to `RATELIMIT_ENABLE`) so local development can disable the guard while staging/production keep it enforced.  
  - Status: Resolved — signup now has dual ratelimiting that respects the existing `RATELIMIT_ENABLE` toggle for local development.

- **Store PKCE code verifier hashes instead of plaintext**  
  - Reference: `mysite/auth/models/google.py:17`  
  - Risk: The `GoogleOAuthState` table retains raw PKCE code verifiers until cleanup. If an attacker gains read access to this table before states expire, they can complete any in-flight OAuth exchange.  
  - Recommendation: Store only a derived hash (e.g., SHA-256) of the code verifier, mirroring how OAuth providers treat authorization codes. Compare hashes during code exchange so a leaked database cannot be used to hijack pending sign-ins.  
  - Status: Resolved — code verifiers are cached short-term, persisted as hashes, and validated on consumption via a new migration.
