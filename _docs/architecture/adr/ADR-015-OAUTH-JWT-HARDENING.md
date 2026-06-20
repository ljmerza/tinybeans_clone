# ADR-015: OAuth & JWT Session Token Hardening

## Status
**Accepted** - *Date: 2026-06-19*

> Builds on [ADR-010: Google OAuth Integration](./ADR-010-GOOGLE-OAUTH-INTEGRATION.md) and the JWT session model introduced alongside it.

---

## Context

### Background
A security review of the authentication system (Google OAuth + JWT sessions) surfaced several issues that were individually low-to-medium severity but collectively weakened the auth posture. None were exploited; the goal of this ADR is to close them proactively.

### Current State (before this ADR)
- **Refresh tokens were neither rotated nor revocable.** `SIMPLE_JWT` had `ROTATE_REFRESH_TOKENS=False`, and `rest_framework_simplejwt.token_blacklist` was **not** installed, so `BLACKLIST_AFTER_ROTATION=True` was a no-op. `LogoutView` only cleared the cookie. A stolen refresh token therefore stayed valid for its full 7-day lifetime, even after logout, with no rotation to bound reuse.
- **Google OAuth requested offline access it never used.** The auth URL set `access_type=offline` + `prompt=consent`, forcing Google to mint a refresh token on every login and forcing the consent screen each time. The app discards Google's tokens (it uses them only to read the verified identity), so this was unnecessary over-permissioning and degraded UX.
- **OAuth state consumption had a race window.** `GoogleOAuthState.mark_as_used()` did a plain `save()`, and the callback marked the state used only *after* the token exchange and user creation. Two concurrent callbacks on the same `state` could both pass validation before either marked it used (TOCTOU).
- **Auth logs contained raw PII.** OAuth/account-linking logs recorded full email addresses and Google `sub` ids at INFO/WARNING level.

### Requirements
- **Always**: a refresh token must be revocable; logout must always succeed.
- **Immediate**: stop requesting Google credentials we discard; make state single-use under concurrency; stop logging raw PII.
- **Constraint**: changes to session-token behavior are app-wide (every login path), so they must not break the SPA's silent-refresh flow.

---

## Decision

Adopt four changes, scoped as one security hardening pass.

### 1. Refresh-token rotation + blacklist + logout revocation
- Set `ROTATE_REFRESH_TOKENS=True` (keep `BLACKLIST_AFTER_ROTATION=True`) in `SIMPLE_JWT`.
- Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` so the `OutstandingToken` / `BlacklistedToken` tables exist and rotation/blacklisting actually take effect.
- On every refresh, the previous refresh token is blacklisted and a new one is issued. `TokenRefreshCookieView` already re-sets the cookie with the rotated token, so no view change was needed there.
- `LogoutView` now blacklists the presented refresh token (best-effort; logout still succeeds for missing/expired/invalid tokens).

**Net effect**: a refresh token is single-use, and logout immediately revokes it. The stolen-token window shrinks from 7 days to "until next legitimate refresh," and logout is now real revocation rather than cookie deletion.

### 2. Google OAuth: request online access only
- Drop `access_type=offline` and `prompt=consent` from the authorization URL; request `access_type=online`.
- Rationale: scopes are `openid email profile` (authentication only). We never call Google APIs on the user's behalf, so a Google refresh token is pure liability. The safest handling of a third-party token is to never receive it.

### 3. Atomic, single-use OAuth state
- `GoogleOAuthState.mark_as_used()` now performs a conditional `UPDATE ... WHERE used_at IS NULL` and returns whether it claimed the row.
- The callback claims the state **immediately after validation and before** the token exchange; a losing race returns the same "invalid state" error as a replay.

### 4. PII redaction in auth logs
- Added `mysite/auth/log_utils.py` with `mask_email()` (`j***@example.com`) and `mask_id()` (`123456...`). OAuth/account-linking log sites now mask email and Google id.

### Explicitly NOT changed
- **OAuth state IP-mismatch remains log-only** (not enforced). Mobile clients legitimately change IP between initiate and callback; enforcing it would cause false logouts. This is an accepted, documented tradeoff (unchanged from ADR-010).

---

## Alternatives Considered

### Logout revocation only (no rotation)
Install `token_blacklist` and blacklist on logout, but keep `ROTATE_REFRESH_TOKENS=False`.
- **Pros**: real logout revocation; no rotation churn; no multi-tab refresh edge case.
- **Cons**: a token stolen mid-session is still valid for 7 days if the user never logs out. Rejected because rotation is the larger security win and the SPA's deduped refresh already handles rotation cleanly.

### Store Google's refresh token (encrypted) instead of dropping offline access
Keep `access_type=offline` and persist the Google refresh token encrypted at rest.
- **Pros**: enables future Google API calls.
- **Cons**: adds a high-value secret at rest for a capability we don't use. Rejected as YAGNI; revisit in its own ADR if/when Google API access is needed.

### Enforce IP binding on OAuth state
- Rejected: breaks legitimate mobile users; low marginal security given state is already single-use, short-lived, and nonce-bound.

---

## Consequences

### Positive
- ✅ **Refresh tokens are single-use and revocable** — bounded theft window, real logout.
- ✅ **No third-party token retained** — nothing to leak; better OAuth UX (no forced consent each login).
- ✅ **State replay/race closed** — exactly-once OAuth callbacks.
- ✅ **Logs no longer store raw email / Google id.**

### Negative / Tradeoffs
- ⚠️ **Migration required on deploy**: `python manage.py migrate` must run to create the `token_blacklist` tables before this ships, or refresh/logout will error.
- ⚠️ **`OutstandingToken` table grows**: rotation writes a row per issued refresh token. Schedule `python manage.py flushexpiredtokens` (e.g. a periodic Celery/cron job) to prune expired entries.
- ⚠️ **Multi-tab refresh edge case**: with rotation, if two browser tabs each hold the pre-rotation cookie and both refresh, the second (stale) request is rejected and that tab is logged out. The SPA's single-context refresh dedup (`web/src/features/auth/utils/refreshToken.ts`) prevents this within one tab; cross-tab is a rare, low-impact case (one tab re-auths). Documented, not mitigated in this PR.

### Risks and Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Deploy without running migration | High (auth 500s) | Medium | Call out migrate in PR/runbook; tables are SimpleJWT-provided |
| OutstandingToken table unbounded growth | Medium | Medium | `flushexpiredtokens` on a schedule |
| Stale-tab logout after rotation | Low | Low | Accepted; user re-authenticates in that tab |

---

## Implementation Details

### Changed files
- `mysite/config/settings/auth.py` — `ROTATE_REFRESH_TOKENS=True`.
- `mysite/config/settings/base.py` — add `token_blacklist` app.
- `mysite/auth/views/account.py` — `LogoutView` blacklists the refresh token.
- `mysite/auth/models/google.py` — atomic `mark_as_used()` returning `bool`.
- `mysite/auth/views/google_oauth/callback.py` — claim state before exchange.
- `mysite/auth/services/oauth/google_api_service.py` — `access_type=online`; masked logs.
- `mysite/auth/services/oauth/account_linking_service.py` — masked logs.
- `mysite/auth/log_utils.py` *(new)* — `mask_email`, `mask_id`.

### Frontend
No change required. `TokenRefreshCookieView` re-sets the rotated cookie and the SPA reads the access token from the response body; the existing deduped refresh handles rotation correctly.

### Migration path
Library-provided migrations only (no app migrations authored):
```bash
python manage.py migrate            # creates token_blacklist tables
python manage.py flushexpiredtokens # schedule periodically
```

---

## Testing Strategy
- **Unit**: `mask_email`/`mask_id` (`test_log_utils.py`); atomic single-winner `mark_as_used` and online-only auth URL (`test_google_oauth_state.py`).
- **Integration**: rotation blacklists the previous refresh token; rotated token still works; logout revokes the token; logout succeeds with missing/invalid cookie (`test_refresh_token_rotation.py`).
- Full backend suite (297 tests) passes with rotation + blacklist enabled.

---

## Related ADRs
- [ADR-010: Google OAuth Integration](./ADR-010-GOOGLE-OAUTH-INTEGRATION.md) — base OAuth/PKCE design this hardens.
- [ADR-003: Two-Factor Authentication](./ADR-003-TWO-FACTOR-AUTHENTICATION.md) — partial tokens / login flow that issues these sessions.
- [ADR-005: CSRF Token Management](./ADR-005-CSRF-TOKEN-MANAGEMENT.md) — cookie security model.

---

## References
- SimpleJWT — Blacklist app & token rotation: https://django-rest-framework-simplejwt.readthedocs.io/en/latest/blacklist_app.html
- OAuth 2.0 for Web Server Apps (`access_type`): https://developers.google.com/identity/protocols/oauth2/web-server

---

## Change History
| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-06-19 | 1.0 | Leonardo Merza | Initial ADR; rotation+revocation, online-only OAuth, atomic state, PII-masked logs |
