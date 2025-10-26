## Large Django Module Split Candidates

### Purpose
- Highlight Django modules/tests that have grown past ~390 lines and now mix multiple responsibilities.
- Give direction for where to split or refactor so future changes stay reviewable and merge-friendly.

### Selection Criteria
- Source files under `mysite/` that exceeded ~390 lines per `wc -l`.
- Priority ordering is by size (largest first) because conflicts and review pain scale with line count.
- Suggestions favor splitting along feature boundaries or extracting helpers into `services.py`.

### Candidates

| File | Lines | Why It Feels Overgrown | Suggested Refactor |
| --- | --- | --- | --- |
| ~~`mysite/auth/views/two_factor.py`~~ | ~~851~~ | ~~Completed: split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (all re-exported from `views/two_factor/__init__.py`).~~ | ~~Completed: split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (all re-exported from `views/two_factor/__init__.py`).~~ |
| ~~`mysite/auth/tests/test_2fa_api.py`~~ | ~~744~~ | ~~One monolithic test module covering every 2FA API permutation with sprawling fixtures.~~ | ~~Completed: replaced with `test_2fa_setup_api.py`, `test_2fa_management_api.py`, `test_2fa_recovery_api.py`, and `test_trusted_devices_api.py` plus a shared helper.~~ |
| `mysite/auth/tests/test_2fa_services.py` | 715 | Mixes TOTPs, SMS, email, and trusted-device service tests, making failures hard to trace. | Break into dedicated modules per service (`test_totp_service.py`, `test_sms_service.py`, etc.) and share fixtures via `conftest.py`. |
| `mysite/users/tests/test_serializers.py` | 580 | Validates many unrelated serializers (profiles, invites, guardians, children) in a single suite. | Group tests by serializer family (e.g., `test_profile_serializers.py`) so contributors can focus on the relevant domain. |
| `mysite/config/settings/base.py` | 567 | Core settings file now mixes auth, storage, Celery, DRF, and feature toggles, making merges noisy. | Extract thematic settings modules (`settings/auth.py`, `settings/storage.py`, `settings/celery.py`) and import them inside `base.py`. |
| `mysite/users/tests/test_edge_cases.py` | 521 | Acts as a dumping ground for diverse edge scenarios across the users domain. | Relocate cases into the closest feature test module and reserve this file for truly cross-cutting safeguards. |
| `mysite/circles/views/invitations.py` | 520 | Handles request, acceptance, reminders, and admin flows in one DRF view module. | Introduce viewsets per action (`request`, `accept`, `admin`) or split by user role while moving shared logic into `services/invitations.py`. |
| `mysite/users/tests/test_invitation_roles.py` | 508 | Comprehensive but dense tests for every invitation role transition. | Divide by role type or state machine phase, and keep reusable scenario builders in fixtures. |
| `mysite/auth/services/google_oauth_service.py` | 485 | Service mixes PKCE state, token exchange, profile sync, and account linking concerns. | Extract sub-services for state storage, Google API interaction, and linking/unlinking to contain complexity. |
| `mysite/auth/views/google.py` | 462 | Initiate, callback, error handling, and linking endpoints coexist, spreading shared helpers everywhere. | Move initiate/callback/link/unlink views into dedicated modules and reuse a `google_oauth/helpers.py`. |
| `mysite/auth/tests/test_2fa_login.py` | 444 | Combines happy-path login, lockouts, rate limits, and trusted-device flows. | Split into login success vs. lockout/rate-limit vs. trusted-device modules so regressions point to the right area. |
| `mysite/auth/tests/test_oauth_service.py` | 420 | Tests cover multiple providers and operations in one file, obscuring failures. | Separate per provider (Google, magic link) or per operation (initiate/callback/link) and dedupe fixtures. |
| `mysite/keeps/views/keeps.py` | 407 | Contains CRUD endpoints plus async upload orchestration and status polling. | Promote uploads/status endpoints into `views/uploads.py` and keep core CRUD logic in `views/keeps.py` or DRF viewsets. |
| `mysite/auth/views/account.py` | 392 | Profile, security, device, and notification settings are combined, complicating edits. | Break into `profile.py`, `security.py`, and `devices.py` modules while consolidating shared serializers/services. |

### Next Actions
- Pick the next production module (e.g., `mysite/circles/views/invitations.py`) and draft a concrete split plan plus ownership.
- After each refactor, add smoke tests (or reorganize existing ones) to confirm module boundaries stayed intact.

### Refactor Progress
- [x] `mysite/auth/views/two_factor.py` split into `setup.py`, `management.py`, `recovery.py`, `trusted_devices.py`, and `login.py` (re-exported via `mysite/auth/views/two_factor/__init__.py`).
- [x] `mysite/auth/tests/test_2fa_api.py` replaced with targeted modules per flow (`test_2fa_setup_api.py`, `test_2fa_management_api.py`, `test_2fa_recovery_api.py`, `test_trusted_devices_api.py`) plus `tests/helpers.py`.
